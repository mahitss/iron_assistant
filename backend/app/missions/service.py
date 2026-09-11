"""Transactional Service Facade for Kairo Autonomous Goal Management & Mission Engine (Task 66)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.missions.audit import MissionAuditor
from app.missions.blockers import BlockerManager
from app.missions.goals import GoalManager
from app.missions.integrator import MissionCrossSystemIntegrator
from app.missions.lifecycle import MissionStateMachine
from app.missions.models import (
    GoalModel,
    MissionModel,
    MissionPostmortemModel,
)
from app.missions.privacy import validate_mission_tenant
from app.missions.progress import ProgressEngine
from app.missions.safety import (
    block_unauthorized_goal_generation,
)
from app.missions.schemas import (
    BlockerStatus,
    Goal,
    GoalAuthorityScope,
    GoalValidationStatus,
    Mission,
    MissionCreateRequest,
    MissionHealth,
    MissionOverview,
    MissionPostmortem,
    MissionStatus,
)
from app.missions.supervisor import MissionSupervisor

logger = logging.getLogger("kairo.missions.service")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionService:
    """High-level transactional service coordinating all Mission Engine capabilities."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.goal_mgr = GoalManager()
        self.blocker_mgr = BlockerManager()
        self.supervisor = MissionSupervisor()
        self.integrator = MissionCrossSystemIntegrator()
        self.auditor = MissionAuditor()
        self._missions: dict[str, Mission] = {}

    # --- Mission Creation & Goal Normalization (Spec 2, 4, 9, 100) ---

    def create_mission(
        self,
        request: MissionCreateRequest,
        actor: str = "user",
        is_human_approved: bool = False,
    ) -> tuple[Mission, Goal, GoalValidationStatus, dict[str, Any]]:
        """Normalize goal and instantiate self-directed mission."""
        # Enforce NO SELF-APPOINTED PURPOSE (Spec 4, 100)
        block_unauthorized_goal_generation(request.origin, is_human_approved=is_human_approved)

        # Normalize natural language goal (Spec 9)
        raw_obj = request.description or request.objective or request.title
        goal, val_status, ambiguity_info = self.goal_mgr.normalize_goal(
            raw_objective=raw_obj,
            origin=request.origin,
            authority_scope=request.authority_scope,
            owner=actor,
            tenant_id=request.tenant_id,
            constraints=request.constraints,
            deadline=request.deadline,
        )

        # Build Mission entity
        mission_id = f"msn_{uuid.uuid4().hex[:10]}"
        b_limits = request.budget_limits or {
            "max_duration_hours": 72.0,
            "max_tool_calls": 500.0,
            "max_cost_usd": float(request.budget_limit) if request.budget_limit is not None else 50.0,
            "max_agent_spawns": 10.0,
        }
        mission = Mission(
            mission_id=mission_id,
            title=request.title or goal.title,
            goal_id=goal.goal_id,
            authority_scope=request.authority_scope,
            status=MissionStatus.READY
            if val_status == GoalValidationStatus.VALID
            else MissionStatus.VALIDATING,
            health=MissionHealth.ON_TRACK,
            budget_limits=b_limits,
            deadline=request.deadline,
            tenant_id=request.tenant_id,
            provenance={"created_by": actor, "origin": request.origin.value},
        )

        # Generate initial strategic plan (v1)
        initial_plan = self.integrator.generate_strategic_plan(mission, goal)
        mission.active_plan_id = initial_plan["plan_id"]

        self._missions[mission.mission_id] = mission

        # Audit Event
        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_CREATED",
            actor=actor,
            authority=mission.authority_scope.value,
            details={"title": mission.title, "goal_id": goal.goal_id, "status": mission.status.value},
        )

        # Database Persistence
        if self.db:
            goal_rec = GoalModel(
                goal_id=goal.goal_id,
                title=goal.title,
                description=goal.description,
                origin=goal.origin.value,
                owner=goal.owner,
                stakeholders_json=goal.stakeholders,
                priority=goal.priority,
                importance=goal.importance,
                urgency=goal.urgency,
                scope_json=goal.scope,
                constraints_json=goal.constraints,
                deadline=goal.deadline,
                success_criteria_json=[c.model_dump() for c in goal.success_criteria],
                failure_conditions_json=[f.model_dump() for f in goal.failure_conditions],
                dependencies_json=goal.dependencies,
                resources_json=goal.resources,
                risk_level=goal.risk_level,
                authority_scope=goal.authority_scope.value,
                status=goal.status.value,
                version=goal.version,
                provenance_json=goal.provenance,
                tenant_id=goal.tenant_id,
            )
            mission_rec = MissionModel(
                mission_id=mission.mission_id,
                title=mission.title,
                goal_id=mission.goal_id,
                authority_scope=mission.authority_scope.value,
                status=mission.status.value,
                health=mission.health.value,
                active_plan_id=mission.active_plan_id,
                plan_versions_json=mission.plan_versions,
                progress_pct=mission.progress_pct,
                budget_limits_json=mission.budget_limits,
                budget_consumed_json=mission.budget_consumed,
                deadline=mission.deadline,
                expires_at=mission.expires_at,
                checkpoints_json=[c.model_dump() for c in mission.checkpoints],
                blockers_json=[b.model_dump() for b in mission.blockers],
                version=mission.version,
                provenance_json=mission.provenance,
                tenant_id=mission.tenant_id,
            )
            self.db.add(goal_rec)
            self.db.add(mission_rec)
            self.db.commit()

        return mission, goal, val_status, ambiguity_info

    # --- Mission Lifecycle Operations ---

    def start_mission(self, mission_id: str, actor: str = "user", tenant_id: str = "default") -> Mission:
        """Move mission from DRAFT/VALIDATING to READY and RUNNING."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        if mission.status == MissionStatus.DRAFT:
            MissionStateMachine.transition(
                mission, MissionStatus.VALIDATING, reason="Pre-flight validation", actor=actor
            )
            MissionStateMachine.transition(
                mission, MissionStatus.READY, reason="Validated and ready", actor=actor
            )

        if mission.status == MissionStatus.READY:
            MissionStateMachine.transition(
                mission, MissionStatus.RUNNING, reason="Execution initiated", actor=actor
            )

        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_STARTED",
            actor=actor,
            authority=mission.authority_scope.value,
            details={"status": mission.status.value},
        )
        self._sync_db_mission(mission)
        return mission

    def pause_mission(
        self,
        mission_id: str,
        reason: str = "User requested pause",
        actor: str = "user",
        tenant_id: str = "default",
    ) -> Mission:
        """Pause mission execution (Spec 48, 73)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        MissionStateMachine.transition(mission, MissionStatus.PAUSED, reason=reason, actor=actor)
        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_PAUSED",
            actor=actor,
            details={"reason": reason},
        )
        self._sync_db_mission(mission)
        return mission

    def resume_mission(self, mission_id: str, actor: str = "user", tenant_id: str = "default") -> Mission:
        """Resume paused mission with revalidation (Spec 48, 49)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        MissionStateMachine.revalidate_and_resume(mission, is_world_valid=True)
        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_RESUMED",
            actor=actor,
            details={"status": mission.status.value},
        )
        self._sync_db_mission(mission)
        return mission

    def cancel_mission(
        self, mission_id: str, reason: str = "User cancelled", actor: str = "user", tenant_id: str = "default"
    ) -> Mission:
        """Gracefully cancel mission and release resources (Spec 74, 90)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        MissionStateMachine.transition(mission, MissionStatus.CANCELLED, reason=reason, actor=actor)
        self.integrator.release_resources(mission)
        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_CANCELLED",
            actor=actor,
            details={"reason": reason},
        )
        self._sync_db_mission(mission)
        return mission

    def replan_mission(
        self,
        mission_id: str,
        reason: str = "Strategy adjustment",
        actor: str = "system",
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Trigger strategic replan without mutating immutable historical plans (Spec 35, 36, 37)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id) or Goal(title=mission.title, description=mission.title)

        if mission.status in (MissionStatus.RUNNING, MissionStatus.BLOCKED, MissionStatus.PAUSED):
            MissionStateMachine.transition(mission, MissionStatus.REPLANNING, reason=reason, actor=actor)

        new_plan = self.integrator.generate_strategic_plan(mission, goal)
        MissionStateMachine.transition(mission, MissionStatus.READY, reason="New plan generated", actor=actor)
        MissionStateMachine.transition(
            mission, MissionStatus.RUNNING, reason="Resumed under new plan", actor=actor
        )

        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_REPLANNED",
            actor=actor,
            details={"new_plan_id": new_plan["plan_id"], "reason": reason},
        )
        self._sync_db_mission(mission)
        return new_plan

    def execute_supervisory_cycle(
        self,
        mission_id: str,
        telemetry: dict[str, Any],
        recent_actions: list[str],
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Run an autonomous supervisory cycle for the active mission."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id) or Goal(title=mission.title, description=mission.title)

        cycle_result = self.supervisor.run_supervisory_cycle(
            mission=mission,
            goal=goal,
            telemetry=telemetry,
            recent_actions=recent_actions,
        )

        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="SUPERVISORY_CYCLE_EXECUTED",
            details={"cycle_status": cycle_result["cycle_status"]},
        )
        self._sync_db_mission(mission)
        return cycle_result

    def complete_mission(
        self,
        mission_id: str,
        what_worked: list[str] | None = None,
        lessons: list[str] | None = None,
        actor: str = "system",
        tenant_id: str = "default",
    ) -> MissionPostmortem:
        """Close mission and record postmortem for continuous learning (Spec 75, 78)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        if mission.status == MissionStatus.DRAFT:
            MissionStateMachine.transition(
                mission, MissionStatus.VALIDATING, reason="Validating before complete", actor=actor
            )
            MissionStateMachine.transition(
                mission, MissionStatus.READY, reason="Ready before complete", actor=actor
            )
        if mission.status in (
            MissionStatus.READY,
            MissionStatus.PAUSED,
            MissionStatus.BLOCKED,
            MissionStatus.REPLANNING,
        ):
            MissionStateMachine.transition(
                mission, MissionStatus.RUNNING, reason="Running before complete", actor=actor
            )
        if mission.status == MissionStatus.RUNNING:
            MissionStateMachine.transition(
                mission, MissionStatus.VERIFYING, reason="Verifying before complete", actor=actor
            )

        postmortem = self.supervisor.close_mission_with_postmortem(
            mission=mission,
            final_status=MissionStatus.COMPLETED,
            what_worked=what_worked,
            lessons=lessons,
        )
        self.integrator.release_resources(mission)

        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_COMPLETED",
            actor=actor,
            details={"postmortem_id": postmortem.postmortem_id},
        )
        self._sync_db_mission(mission)

        if self.db:
            pm_rec = MissionPostmortemModel(
                postmortem_id=postmortem.postmortem_id,
                mission_id=postmortem.mission_id,
                final_status=postmortem.final_status.value,
                what_worked_json=postmortem.what_worked,
                what_failed_json=postmortem.what_failed,
                unexpected_events_json=postmortem.unexpected_events,
                planning_errors_json=postmortem.planning_errors,
                resource_problems_json=postmortem.resource_problems,
                agent_performance_json=postmortem.agent_performance,
                lessons_json=postmortem.lessons,
                completed_at=postmortem.completed_at,
            )
            self.db.add(pm_rec)
            self.db.commit()

        return postmortem

    # --- Query & Overview Operations ---

    def get_mission(self, mission_id: str, tenant_id: str = "default") -> Mission:
        """Retrieve mission with tenant isolation check."""
        mission = self._missions.get(mission_id)
        if not mission and self.db:
            rec = self.db.query(MissionModel).filter(MissionModel.mission_id == mission_id).first()
            if rec:
                mission = Mission(
                    mission_id=rec.mission_id,
                    title=rec.title,
                    goal_id=rec.goal_id,
                    authority_scope=GoalAuthorityScope(rec.authority_scope),
                    status=MissionStatus(rec.status),
                    health=MissionHealth(rec.health),
                    active_plan_id=rec.active_plan_id,
                    plan_versions=rec.plan_versions_json or [],
                    progress_pct=rec.progress_pct,
                    budget_limits=rec.budget_limits_json or {},
                    budget_consumed=rec.budget_consumed_json or {},
                    deadline=rec.deadline,
                    expires_at=rec.expires_at,
                    version=rec.version,
                    provenance=rec.provenance_json or {},
                    tenant_id=rec.tenant_id,
                )
                self._missions[mission.mission_id] = mission

        if not mission:
            raise KeyError(f"Mission '{mission_id}' not found.")

        validate_mission_tenant(mission.tenant_id, tenant_id, mission_id)
        return mission

    def list_missions(self, tenant_id: str = "default") -> list[Mission]:
        return [m for m in self._missions.values() if m.tenant_id == tenant_id]

    def get_overview(self, tenant_id: str = "default") -> MissionOverview:
        missions = self.list_missions(tenant_id=tenant_id)
        active = sum(1 for m in missions if m.status in (MissionStatus.RUNNING, MissionStatus.PLANNING))
        blocked = sum(1 for m in missions if m.status == MissionStatus.BLOCKED)
        completed = sum(1 for m in missions if m.status == MissionStatus.COMPLETED)
        failed = sum(1 for m in missions if m.status == MissionStatus.FAILED)
        open_blockers = sum(
            len([b for b in m.blockers if b.status != BlockerStatus.RESOLVED]) for m in missions
        )

        return MissionOverview(
            total_missions=len(missions),
            active_missions=active,
            healthy_count=sum(1 for m in missions if m.health == MissionHealth.ON_TRACK),
            blocked_missions=blocked,
            completed_missions=completed,
            failed_missions=failed,
            open_blockers=open_blockers,
            active_drifts=sum(1 for m in missions if m.health == MissionHealth.DRIFTING),
            audit_chain_intact=self.auditor.verify_integrity(),
            missions=missions,
        )

    def get_mission_goals(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve goal hierarchy, constraints, success criteria, and DAG for mission (Spec 3, 12, 13, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id)
        goal_data = goal.model_dump() if goal else {"goal_id": mission.goal_id, "title": mission.title}
        return {
            "mission_id": mission.mission_id,
            "primary_goal": goal_data,
            "dag_dependencies": self.goal_mgr._goal_dag.get(mission.goal_id, []),
            "hierarchy_level": "MISSION",
        }

    def get_mission_tasks(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve active planning tasks associated with mission (Spec 31, 32, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id) or Goal(title=mission.title, description=mission.title)
        plan = self.integrator.generate_strategic_plan(mission, goal)
        return {
            "mission_id": mission.mission_id,
            "active_plan_id": mission.active_plan_id or plan["plan_id"],
            "plan_version": len(mission.plan_versions),
            "tasks": plan.get("tasks", []),
        }

    def get_mission_progress(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve multi-metric progress calculations, milestones, and sunk cost status (Spec 27, 28, 34, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id)
        total_crit = len(goal.success_criteria) if goal else 0
        verified_crit = sum(1 for c in goal.success_criteria if c.is_verified) if goal else 0
        sunk_cost_alert, sunk_cost_msg = ProgressEngine.evaluate_sunk_cost(
            consecutive_failures=0,
            cost_incurred=mission.budget_consumed.get("cost_usd", 0.0),
            expected_future_value=0.8,
        )
        return {
            "mission_id": mission.mission_id,
            "progress_pct": mission.progress_pct,
            "health": mission.health.value,
            "status": mission.status.value,
            "verified_criteria_count": verified_crit,
            "total_criteria_count": total_crit,
            "sunk_cost_alert": sunk_cost_alert,
            "sunk_cost_status": sunk_cost_msg,
            "checkpoints_count": len(mission.checkpoints),
        }

    def get_mission_blockers(self, mission_id: str, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Retrieve prioritized blockers halting mission progress (Spec 68, 69, 70, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        prioritized = self.blocker_mgr.prioritize_blockers(mission.blockers)
        return [b.model_dump() for b in prioritized]

    def get_mission_timeline(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve complete mission replay timeline and checkpoints (Spec 82, 83, 94, 96)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        audit_events = self.auditor.get_trail(mission_id=mission.mission_id)
        return {
            "mission_id": mission.mission_id,
            "created_at": mission.created_at.isoformat(),
            "updated_at": mission.updated_at.isoformat(),
            "checkpoints": [c.model_dump() for c in mission.checkpoints],
            "audit_events": [a.model_dump() for a in audit_events],
        }

    def get_mission_decisions(self, mission_id: str, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Retrieve decision engine trade-offs and alternatives evaluated (Spec 51, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        decision = self.integrator.evaluate_decision_alternatives(
            mission=mission,
            decision_context=f"Strategic pathway decision for mission {mission.title}",
            alternatives=[
                "Path A (High-throughput parallel execution)",
                "Path B (Conservative verified staging)",
            ],
        )
        return [decision]

    def get_mission_risks(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve risk evaluation, failure conditions, and drift indicators (Spec 11, 19, 20, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id)
        return {
            "mission_id": mission.mission_id,
            "risk_level": goal.risk_level if goal else 0.2,
            "failure_conditions": [fc.model_dump() for fc in goal.failure_conditions] if goal else [],
            "health": mission.health.value,
            "is_drifting": mission.health == MissionHealth.DRIFTING,
            "is_blocked": mission.health == MissionHealth.BLOCKED,
        }

    def reassess_mission(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Revalidate assumptions against World Model & Foresight (Spec 21, 22, 53, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id) or Goal(title=mission.title, description=mission.title)
        world_check = self.integrator.query_world_assumptions(mission, goal)

        if not world_check.get("assumptions_valid", True):
            MissionStateMachine.transition(
                mission, MissionStatus.REPLANNING, reason="Assumptions invalidated by World Model"
            )
            mission.health = MissionHealth.AT_RISK

        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_REASSESSED",
            details=world_check,
        )
        self._sync_db_mission(mission)
        return world_check

    def verify_mission(
        self, mission_id: str, telemetry: dict[str, Any] | None = None, tenant_id: str = "default"
    ) -> dict[str, Any]:
        """Empirically verify success criteria against telemetry (Spec 65, 75, 76, 94)."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id)
        readings = telemetry or {}

        if not goal:
            return {"verified": False, "reasons": ["No associated goal found."]}

        all_passed, reasons = ProgressEngine.evaluate_goal_success(goal, readings)
        if all_passed:
            if mission.status == MissionStatus.RUNNING:
                MissionStateMachine.transition(
                    mission, MissionStatus.VERIFYING, reason="Success criteria verified"
                )
        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_VERIFIED",
            details={"all_passed": all_passed, "reasons": reasons},
        )
        self._sync_db_mission(mission)
        return {
            "mission_id": mission.mission_id,
            "verified": all_passed,
            "reasons": reasons,
            "current_status": mission.status.value,
        }

    def _sync_db_mission(self, mission: Mission) -> None:
        """Update persistent database record."""
        if self.db:
            rec = self.db.query(MissionModel).filter(MissionModel.mission_id == mission.mission_id).first()
            if rec:
                rec.status = mission.status.value
                rec.health = mission.health.value
                rec.active_plan_id = mission.active_plan_id
                rec.plan_versions_json = mission.plan_versions
                rec.progress_pct = mission.progress_pct
                rec.budget_consumed_json = mission.budget_consumed
                rec.checkpoints_json = [c.model_dump() for c in mission.checkpoints]
                rec.blockers_json = [b.model_dump() for b in mission.blockers]
                rec.version = mission.version
                rec.updated_at = _now_utc()
                self.db.commit()


# Subsystem singleton instance
mission_service = MissionService()
