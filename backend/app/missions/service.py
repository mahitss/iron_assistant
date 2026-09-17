"""Transactional Service Facade for Kairo Autonomous Goal Management & Mission Control (Task 66 & Task 100)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.missions.assumptions import AssumptionTracker
from app.missions.audit import MissionAuditor
from app.missions.blockers import BlockerManager
from app.missions.checkpoints import MissionCheckpointEngine
from app.missions.goals import GoalManager
from app.missions.health import MissionHealthEngine
from app.missions.integrator import MissionCrossSystemIntegrator
from app.missions.lifecycle import MissionStateMachine
from app.missions.milestones import MilestoneEngine
from app.missions.models import (
    GoalModel,
    MissionAssumptionModel,
    MissionDependencyModel,
    MissionMilestoneModel,
    MissionModel,
    MissionObjectiveModel,
    MissionPlanVersionModel,
    MissionPostmortemModel,
    MissionReviewModel,
)
from app.missions.orchestrator import MissionControlOrchestrator
from app.missions.privacy import validate_mission_tenant
from app.missions.progress import ProgressEngine
from app.missions.replanning import PlanVersionManager
from app.missions.safety import (
    block_unauthorized_goal_generation,
)
from app.missions.schemas import (
    AssumptionCreateRequest,
    AssumptionStatus,
    AssumptionUpdateRequest,
    AutonomyLevel,
    Blocker,
    BlockerSeverity,
    BlockerStatus,
    DependencyCreateRequest,
    DependencyStatus,
    DependencyType,
    Goal,
    GoalAuthorityScope,
    GoalValidationStatus,
    MilestoneCreateRequest,
    MilestoneStatus,
    MilestoneUpdateRequest,
    MilestoneVerifyRequest,
    Mission,
    MissionAssumption,
    MissionCheckpoint,
    MissionCreateRequest,
    MissionDependency,
    MissionHealth,
    MissionHealthDimensions,
    MissionMilestone,
    MissionObjective,
    MissionOverview,
    MissionPlanVersion,
    MissionPostmortem,
    MissionReview,
    MissionStatus,
    MissionUpdateRequest,
    ObjectiveCreateRequest,
    ReviewType,
    SuccessCriteria,
)
from app.missions.supervisor import MissionSupervisor

logger = logging.getLogger("kairo.missions.service")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionService:
    """High-level transactional service coordinating all Mission Control & Long-Horizon capabilities."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.goal_mgr = GoalManager()
        self.blocker_mgr = BlockerManager()
        self.supervisor = MissionSupervisor()
        self.integrator = MissionCrossSystemIntegrator()
        self.auditor = MissionAuditor()
        self.orchestrator = MissionControlOrchestrator()
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
            description=request.description or "",
            objective=request.objective or raw_obj,
            scope=request.scope or "SYSTEM",
            goal_id=goal.goal_id,
            authority_scope=request.authority_scope,
            autonomy_level=request.autonomy_level,
            status=MissionStatus.READY
            if val_status == GoalValidationStatus.VALID
            else MissionStatus.VALIDATING,
            health=MissionHealth.ON_TRACK,
            priority=request.priority,
            strategic_importance=request.importance,
            budget_limits=b_limits,
            deadline=request.deadline,
            tenant_id=request.tenant_id,
            provenance={"created_by": actor, "origin": request.origin.value},
        )

        # Initialize health dimensions
        MissionHealthEngine.evaluate_health(mission)

        # Generate initial strategic plan (v1)
        initial_plan = self.integrator.generate_strategic_plan(mission, goal)
        mission.active_plan_id = initial_plan["plan_id"]
        PlanVersionManager.record_plan_version(
            mission=mission,
            plan_id=initial_plan["plan_id"],
            plan_spec=initial_plan,
            reason="Initial strategic plan synthesis upon mission creation",
            decisions_linked=["dec_init"],
        )

        self._missions[mission.mission_id] = mission

        # Audit Event
        self.auditor.record_event(
            mission_id=mission.mission_id,
            event_type="MISSION_CREATED",
            actor=actor,
            authority=mission.authority_scope.value,
            details={"title": mission.title, "goal_id": goal.goal_id, "status": mission.status.value},
        )

        # Persist to relational storage if db session is present
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
                description=mission.description,
                objective=mission.objective,
                scope=mission.scope,
                goal_id=mission.goal_id,
                authority_scope=mission.authority_scope.value,
                autonomy_level=mission.autonomy_level.value,
                status=mission.status.value,
                health=mission.health.value,
                health_dimensions_json=mission.health_dimensions.model_dump(),
                priority=mission.priority,
                strategic_importance=mission.strategic_importance,
                active_plan_id=mission.active_plan_id,
                plan_versions_json=mission.plan_versions,
                progress_pct=mission.progress_pct,
                progress_confidence=mission.progress_confidence,
                uncertainty=mission.uncertainty,
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
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()

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

        if mission.status in (MissionStatus.RUNNING, MissionStatus.ACTIVE, MissionStatus.BLOCKED, MissionStatus.PAUSED):
            MissionStateMachine.transition(mission, MissionStatus.REPLANNING, reason=reason, actor=actor)

        new_plan = self.integrator.generate_strategic_plan(mission, goal)
        PlanVersionManager.record_plan_version(
            mission=mission,
            plan_id=new_plan["plan_id"],
            plan_spec=new_plan,
            reason=reason,
            decisions_linked=["dec_replanned"],
        )

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
        if mission.status in (MissionStatus.RUNNING, MissionStatus.ACTIVE):
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
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()

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
                    description=rec.description,
                    objective=getattr(rec, "objective", "") or "",
                    scope=getattr(rec, "scope", "SYSTEM") or "SYSTEM",
                    goal_id=rec.goal_id,
                    authority_scope=GoalAuthorityScope(rec.authority_scope),
                    autonomy_level=AutonomyLevel(getattr(rec, "autonomy_level", "BOUNDED_AUTONOMY") or "BOUNDED_AUTONOMY"),
                    status=MissionStatus(rec.status),
                    health=MissionHealth(rec.health),
                    active_plan_id=rec.active_plan_id,
                    plan_versions=rec.plan_versions_json or [],
                    progress_pct=rec.progress_pct,
                    progress_confidence=getattr(rec, "progress_confidence", 1.0) or 1.0,
                    strategic_importance=getattr(rec, "strategic_importance", 0.5) or 0.5,
                    uncertainty=getattr(rec, "uncertainty", 0.0) or 0.0,
                    health_dimensions=MissionHealthDimensions(**(getattr(rec, "health_dimensions_json", {}) or {})),
                    risk_summary=getattr(rec, "risk_summary_json", {}) or {},
                    active_situations=getattr(rec, "active_situations_json", []) or [],
                    active_decisions=getattr(rec, "active_decisions_json", []) or [],
                    active_actions=getattr(rec, "active_actions_json", []) or [],
                    active_workflows=getattr(rec, "active_workflows_json", []) or [],
                    active_agents=getattr(rec, "active_agents_json", []) or [],
                    budget_limits=rec.budget_limits_json or {},
                    budget_consumed=rec.budget_consumed_json or {},
                    deadline=rec.deadline,
                    expires_at=rec.expires_at,
                    started_at=getattr(rec, "started_at", None),
                    completed_at=getattr(rec, "completed_at", None),
                    last_review_at=getattr(rec, "last_review_at", None),
                    next_review_at=getattr(rec, "next_review_at", None),
                    current_context_id=getattr(rec, "current_context_id", None),
                    checkpoints=[MissionCheckpoint(**c) for c in (rec.checkpoints_json or [])],
                    blockers=[Blocker(**b) for b in (rec.blockers_json or [])],
                    version=rec.version,
                    provenance=rec.provenance_json or {},
                    tenant_id=rec.tenant_id,
                )
                self._missions[mission.mission_id] = mission

        if not mission:
            raise KeyError(f"Mission '{mission_id}' not found.")

        validate_mission_tenant(mission.tenant_id, tenant_id, mission_id)
        return mission

    def update_mission(self, mission_id: str, request: MissionUpdateRequest, tenant_id: str = "default") -> Mission:
        """Update mutable attributes of a mission."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        if request.title is not None:
            mission.title = request.title
        if request.description is not None:
            mission.description = request.description
        if request.objective is not None:
            mission.objective = request.objective
        if request.autonomy_level is not None:
            mission.autonomy_level = request.autonomy_level
        if request.priority is not None:
            mission.priority = request.priority
        if request.deadline is not None:
            mission.deadline = request.deadline
        if request.strategic_importance is not None:
            mission.strategic_importance = request.strategic_importance
        mission.updated_at = _now_utc()
        self._sync_db_mission(mission)
        return mission

    def list_missions(self, tenant_id: str = "default") -> list[Mission]:
        return [m for m in self._missions.values() if m.tenant_id == tenant_id]

    def get_overview(self, tenant_id: str = "default") -> MissionOverview:
        missions = self.list_missions(tenant_id=tenant_id)
        active = sum(1 for m in missions if m.status in (MissionStatus.RUNNING, MissionStatus.ACTIVE, MissionStatus.PLANNING, MissionStatus.EXECUTING))
        blocked = sum(1 for m in missions if m.status == MissionStatus.BLOCKED)
        at_risk = sum(1 for m in missions if m.status == MissionStatus.AT_RISK)
        awaiting_user = sum(1 for m in missions if m.status == MissionStatus.AWAITING_USER)
        awaiting_approval = sum(1 for m in missions if m.status in (MissionStatus.AWAITING_APPROVAL, MissionStatus.WAITING_FOR_APPROVAL))
        completed = sum(1 for m in missions if m.status == MissionStatus.COMPLETED)
        failed = sum(1 for m in missions if m.status == MissionStatus.FAILED)
        unknown = sum(1 for m in missions if m.status == MissionStatus.UNKNOWN)
        open_blockers = sum(
            len([b for b in m.blockers if b.status != BlockerStatus.RESOLVED]) for m in missions
        )

        return MissionOverview(
            total_missions=len(missions),
            active_missions=active,
            healthy_count=sum(1 for m in missions if m.health == MissionHealth.ON_TRACK),
            blocked_missions=blocked,
            at_risk_missions=at_risk,
            awaiting_user_missions=awaiting_user,
            awaiting_approval_missions=awaiting_approval,
            completed_missions=completed,
            failed_missions=failed,
            unknown_missions=unknown,
            open_blockers=open_blockers,
            active_drifts=sum(1 for m in missions if m.health == MissionHealth.DRIFTING),
            audit_chain_intact=self.auditor.verify_integrity(),
            missions=missions,
        )

    # --- Task 100 Objective & Milestone Operations ---

    def add_objective(self, mission_id: str, request: ObjectiveCreateRequest, tenant_id: str = "default") -> MissionObjective:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        criteria = [SuccessCriteria(**c) for c in (request.success_criteria or [])]
        obj = MissionObjective(
            mission_id=mission.mission_id,
            parent_objective_id=request.parent_objective_id,
            title=request.title,
            description=request.description,
            ordering=request.ordering or (len(mission.objectives) + 1),
            success_criteria=criteria,
        )
        mission.objectives.append(obj)
        mission.updated_at = _now_utc()
        self._sync_db_mission(mission)
        return obj

    def list_objectives(self, mission_id: str, tenant_id: str = "default") -> list[MissionObjective]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        return mission.objectives

    def add_milestone(self, mission_id: str, request: MilestoneCreateRequest, tenant_id: str = "default") -> MissionMilestone:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        criteria = [SuccessCriteria(**c) for c in (request.success_criteria or [])]
        milestone = MilestoneEngine.add_milestone(
            mission=mission,
            title=request.title,
            description=request.description,
            objective_id=request.objective_id,
            ordering=request.ordering,
            dependencies=request.dependencies,
            goal_linkage=request.goal_linkage,
            success_criteria=criteria,
            verification_criteria=request.verification_criteria,
            deadline=request.deadline,
        )
        self._sync_db_mission(mission)
        return milestone

    def list_milestones(self, mission_id: str, tenant_id: str = "default") -> list[MissionMilestone]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        return mission.milestones

    def get_milestone(self, mission_id: str, milestone_id: str, tenant_id: str = "default") -> MissionMilestone:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        for m in mission.milestones:
            if m.milestone_id == milestone_id:
                return m
        raise KeyError(f"Milestone '{milestone_id}' not found on mission '{mission_id}'.")

    def update_milestone(
        self,
        mission_id: str,
        milestone_id: str,
        request: MilestoneUpdateRequest,
        tenant_id: str = "default",
    ) -> MissionMilestone:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        milestone = self.get_milestone(mission_id, milestone_id, tenant_id=tenant_id)
        if request.status is not None:
            milestone.status = request.status
        if request.progress_pct is not None:
            milestone.progress_pct = request.progress_pct
        if request.blocked_reason is not None:
            milestone.blocked_reason = request.blocked_reason
        if request.confidence is not None:
            milestone.confidence = request.confidence
        milestone.updated_at = _now_utc()
        self._sync_db_mission(mission)
        return milestone

    def verify_milestone(
        self,
        mission_id: str,
        milestone_id: str,
        request: MilestoneVerifyRequest,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        ws_data = None
        if request.world_state_entity_id:
            from app.missions.bridges import WorldStateBridge
            ws_entity = WorldStateBridge.get_entity_state(request.world_state_entity_id)
            ws_data = {"reconciled": request.postconditions_matched if request.postconditions_matched is not None else True, "entity": ws_entity}

        success, msg = MilestoneEngine.verify_milestone(
            mission=mission,
            milestone_id=milestone_id,
            empirical_evidence=request.evidence,
            world_state_data=ws_data,
        )
        self._sync_db_mission(mission)
        status_val = "COMPLETED" if success else "FAILED"
        for m in mission.milestones:
            if m.milestone_id == milestone_id:
                status_val = m.status.value
                break
        return {"verified": success, "status": status_val, "message": msg, "milestone_id": milestone_id}

    def regress_milestone(
        self,
        mission_id: str,
        milestone_id: str,
        reason: str,
        evidence: list[str] | None = None,
        tenant_id: str = "default",
    ) -> MissionMilestone:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        m = MilestoneEngine.regress_milestone(mission, milestone_id, reason=reason, evidence=evidence)
        self._sync_db_mission(mission)
        return m

    # --- Task 100 Assumption Operations ---

    def add_assumption(self, mission_id: str, request: AssumptionCreateRequest, tenant_id: str = "default") -> MissionAssumption:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        assumption = AssumptionTracker.add_assumption(
            mission=mission,
            statement=request.statement,
            evidence=request.evidence,
            confidence=request.confidence,
            dependent_milestones=request.dependent_milestones,
            dependent_plan_versions=request.dependent_plan_versions,
        )
        self._sync_db_mission(mission)
        return assumption

    def list_assumptions(self, mission_id: str, tenant_id: str = "default") -> list[MissionAssumption]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        return mission.assumptions

    def update_assumption(
        self,
        mission_id: str,
        assumption_id: str,
        request: AssumptionUpdateRequest,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        if request.status == AssumptionStatus.INVALID:
            res = AssumptionTracker.invalidate_assumption(
                mission=mission,
                assumption_id=assumption_id,
                reason=request.invalidation_reason or "Operator declared assumption invalid",
                evidence=request.evidence,
            )
            self._sync_db_mission(mission)
            return res

        for a in mission.assumptions:
            if a.assumption_id == assumption_id:
                if request.confidence is not None:
                    a.confidence = request.confidence
                if request.evidence:
                    a.evidence.extend(request.evidence)
                if request.status is not None:
                    a.status = request.status
                a.last_verified_at = _now_utc()
                self._sync_db_mission(mission)
                return a.model_dump()
        raise KeyError(f"Assumption '{assumption_id}' not found on mission '{mission_id}'.")

    # --- Task 100 Dependency Operations ---

    def add_dependency(self, mission_id: str, request: DependencyCreateRequest, tenant_id: str = "default") -> MissionDependency:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        dep = MissionDependency(
            mission_id=mission.mission_id,
            name=request.name,
            dependency_type=request.dependency_type,
            status=request.status,
            details=request.details,
            blocking_reason=request.blocking_reason,
        )
        mission.dependencies.append(dep)
        mission.updated_at = _now_utc()
        self._sync_db_mission(mission)
        return dep

    def list_dependencies(self, mission_id: str, tenant_id: str = "default") -> list[MissionDependency]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        return mission.dependencies

    # --- Task 100 Situation & Plan Linkage ---

    def link_situation(self, mission_id: str, situation_id: str, tenant_id: str = "default") -> dict[str, Any]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        if situation_id not in mission.active_situations:
            mission.active_situations.append(situation_id)
            mission.updated_at = _now_utc()
            self._sync_db_mission(mission)
        return {"mission_id": mission_id, "linked_situation": situation_id, "active_situations": mission.active_situations}

    def list_situations(self, mission_id: str, tenant_id: str = "default") -> list[str]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        return mission.active_situations

    def list_plans(self, mission_id: str, tenant_id: str = "default") -> list[MissionPlanVersion]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        return mission.plan_records

    # --- Task 100 Reviews, Health & Checkpoints ---

    def review_mission(
        self,
        mission_id: str,
        reviewer: str = "operator",
        review_type: ReviewType = ReviewType.SCHEDULED,
        notes: str = "",
        evaluation_score: float | None = None,
        observations: list[str] | None = None,
        tenant_id: str = "default",
    ) -> MissionReview:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        health, health_dims = MissionHealthEngine.evaluate_health(mission)
        findings_list = [notes] if notes else [f"Health evaluated as {health.value}"]
        if observations:
            findings_list.extend(observations)
        review = MissionReview(
            mission_id=mission.mission_id,
            reviewer=reviewer,
            review_type=review_type,
            evaluation_score=evaluation_score if evaluation_score is not None else 1.0,
            health_dimensions=health_dims,
            findings=findings_list,
            observations=observations or [],
            recommendations=[f"Current progress at {mission.progress_pct}%"],
            actions_taken=["Scheduled health review logged"],
            reviewed_at=_now_utc(),
        )
        mission.reviews.append(review)
        mission.last_review_at = _now_utc()
        mission.updated_at = _now_utc()
        self._sync_db_mission(mission)
        return review

    def get_mission_health(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        health, health_dims = MissionHealthEngine.evaluate_health(mission)
        critical_path = MilestoneEngine.analyze_critical_path(mission)
        return {
            "mission_id": mission.mission_id,
            "health": health.value,
            "health_dimensions": health_dims.model_dump(),
            "critical_path": critical_path,
        }

    def create_checkpoint(
        self,
        mission_id: str,
        label: str = "",
        context_summary: str = "",
        generate_handoff_manifest: bool = False,
        tenant_id: str = "default",
    ) -> MissionCheckpoint:
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        chk = MissionCheckpointEngine.create_checkpoint(
            mission=mission,
            label=label,
            context_summary=context_summary,
            generate_handoff_manifest=generate_handoff_manifest,
        )
        self._sync_db_mission(mission)
        return chk

    def run_orchestration_cycle(
        self,
        mission_id: str,
        world_state_entity_id: str | None = None,
        expected_postconditions: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Execute one continuous orchestration step."""
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        goal = self.goal_mgr.get_goal(mission.goal_id) or Goal(title=mission.title, description=mission.title)
        res = self.orchestrator.run_orchestration_cycle(
            mission=mission,
            goal=goal,
            world_state_entity_id=world_state_entity_id,
            expected_postconditions=expected_postconditions,
        )
        self._sync_db_mission(mission)
        return res

    # --- Legacy Getters preserved ---

    def get_mission_goals(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
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
        mission = self.get_mission(mission_id, tenant_id=tenant_id)
        prioritized = self.blocker_mgr.prioritize_blockers(mission.blockers)
        return [b.model_dump() for b in prioritized]

    def get_mission_timeline(self, mission_id: str, tenant_id: str = "default") -> dict[str, Any]:
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
                rec.scope = mission.scope
                rec.objective = mission.objective
                rec.autonomy_level = mission.autonomy_level.value
                rec.active_plan_id = mission.active_plan_id
                rec.plan_versions_json = mission.plan_versions
                rec.progress_pct = mission.progress_pct
                rec.progress_confidence = mission.progress_confidence
                rec.strategic_importance = mission.strategic_importance
                rec.uncertainty = mission.uncertainty
                rec.health_dimensions_json = mission.health_dimensions.model_dump()
                rec.risk_summary_json = mission.risk_summary
                rec.active_situations_json = mission.active_situations
                rec.active_decisions_json = mission.active_decisions
                rec.active_actions_json = mission.active_actions
                rec.active_workflows_json = mission.active_workflows
                rec.active_agents_json = mission.active_agents
                rec.budget_consumed_json = mission.budget_consumed
                rec.checkpoints_json = [c.model_dump() for c in mission.checkpoints]
                rec.blockers_json = [b.model_dump() for b in mission.blockers]
                rec.version = mission.version
                rec.started_at = mission.started_at
                rec.completed_at = mission.completed_at
                rec.last_review_at = mission.last_review_at
                rec.next_review_at = mission.next_review_at
                rec.current_context_id = mission.current_context_id
                rec.updated_at = _now_utc()
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()


# Subsystem singleton instance
mission_service = MissionService()
