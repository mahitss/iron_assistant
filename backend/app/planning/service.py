"""Transactional facade service and repository coordinator for Strategic Planning (Task 58)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.planning.audit import plan_auditor
from app.planning.critical_path import critical_path_engine
from app.planning.dependencies import dependency_graph_engine
from app.planning.engine import strategic_planning_engine
from app.planning.outcomes import outcome_tracker
from app.planning.plans import plan_lifecycle_manager
from app.planning.progress import progress_tracker
from app.planning.risks import plan_risk_engine
from app.planning.safety import PlanStaleError, sanitize_plan_directive
from app.planning.schemas import (
    CurrentStateAssessment,
    DesiredStateDefinition,
    HealthStatus,
    PlanOutcome,
    PlanRevision,
    PlanStatus,
    StrategicPlan,
    StrategyOption,
)

logger = logging.getLogger(__name__)


class PlanningService:
    """Production service coordinating strategic planning operations, validation, audits, and transitions."""

    def __init__(self) -> None:
        # In-memory store for high-throughput and state tracking
        self._plans: dict[str, StrategicPlan] = {}
        self._revisions: dict[str, list[PlanRevision]] = {}
        self._outcomes: dict[str, list[PlanOutcome]] = {}

    def create_plan(
        self,
        name: str,
        purpose: str,
        current_state: CurrentStateAssessment | dict[str, Any],
        desired_state: DesiredStateDefinition | dict[str, Any],
        goal_id: str | None = None,
        strategy_option: StrategyOption | dict[str, Any] | None = None,
        author: str = "SYSTEM_USER",
        deadline: datetime | None = None,
        decision_id: str | None = None,
    ) -> StrategicPlan:
        """Create and register a new strategic plan."""
        # Sanitize text
        clean_name = sanitize_plan_directive(name)
        clean_purpose = sanitize_plan_directive(purpose)

        curr_state_obj = (
            CurrentStateAssessment(**current_state) if isinstance(current_state, dict) else current_state
        )
        des_state_obj = (
            DesiredStateDefinition(**desired_state) if isinstance(desired_state, dict) else desired_state
        )
        strat_obj = (
            StrategyOption(**strategy_option)
            if isinstance(strategy_option, dict)
            else strategy_option
        )

        plan = strategic_planning_engine.synthesize_strategic_plan(
            name=clean_name,
            purpose=clean_purpose,
            current_state=curr_state_obj,
            desired_state=des_state_obj,
            goal_id=goal_id,
            strategy_option=strat_obj,
            author=author,
            deadline=deadline,
            decision_id=decision_id,
        )

        self._plans[plan.plan_id] = plan
        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="PLAN_CREATED",
            actor=author,
            details={"name": plan.name, "strategy": plan.strategy.name, "tasks_count": len(plan.tasks)},
        )
        return plan

    def get_plan(self, plan_id: str) -> StrategicPlan | None:
        """Retrieve plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self) -> list[StrategicPlan]:
        """List all active strategic plans."""
        return list(self._plans.values())

    def validate_plan(
        self,
        plan_id: str,
        known_resources: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Validate plan completeness, dependencies, resources, and freshness."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": f"Plan '{plan_id}' not found."}

        val_result = plan_lifecycle_manager.validate_plan(plan, known_system_resources=known_resources)
        if val_result.is_valid and plan.status == PlanStatus.DRAFT:
            plan.status = PlanStatus.VALIDATED

        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="PLAN_VALIDATED",
            actor="VALIDATOR",
            details={"is_valid": val_result.is_valid, "errors": val_result.errors},
        )
        return val_result.to_dict()

    def analyze_plan(self, plan_id: str) -> dict[str, Any]:
        """Deep analysis of critical path, waves, and risk."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": f"Plan '{plan_id}' not found."}
        return strategic_planning_engine.analyze_plan(plan)

    def start_plan(self, plan_id: str, actor: str) -> tuple[bool, str]:
        """Start plan execution wave sequencing after re-verifying freshness.

        INVARIANT 13: Stale plans require revalidation.
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return False, f"Plan '{plan_id}' not found."

        if not plan_lifecycle_manager.check_plan_freshness(plan):
            raise PlanStaleError(
                f"Cannot start plan '{plan_id}'. Environment or plan state is STALE. Revalidation required."
            )

        if plan.status in (PlanStatus.RUNNING, PlanStatus.COMPLETED, PlanStatus.CANCELLED):
            return False, f"Plan is already in status {plan.status}."

        plan.status = PlanStatus.RUNNING
        plan.updated_at = datetime.now(timezone.utc)
        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="PLAN_STARTED",
            actor=actor,
            details={"version": plan.version},
        )
        return True, "Plan marked RUNNING. Execution waves queued."

    def pause_plan(self, plan_id: str, actor: str, reason: str = "Operator requested pause.") -> tuple[bool, str]:
        """Pause a currently running plan."""
        plan = self.get_plan(plan_id)
        if not plan:
            return False, f"Plan '{plan_id}' not found."

        if plan.status != PlanStatus.RUNNING:
            return False, f"Cannot pause plan in status {plan.status}."

        plan.status = PlanStatus.PAUSED
        plan.updated_at = datetime.now(timezone.utc)
        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="PLAN_PAUSED",
            actor=actor,
            details={"reason": reason},
        )
        return True, "Plan successfully PAUSED."

    def resume_plan(self, plan_id: str, actor: str) -> tuple[bool, str]:
        """Resume a paused plan, revalidating environment state."""
        plan = self.get_plan(plan_id)
        if not plan:
            return False, f"Plan '{plan_id}' not found."

        if plan.status != PlanStatus.PAUSED:
            return False, f"Cannot resume plan in status {plan.status}."

        if not plan_lifecycle_manager.check_plan_freshness(plan):
            raise PlanStaleError("Cannot resume plan. Plan state expired during pause.")

        plan.status = PlanStatus.RUNNING
        plan.updated_at = datetime.now(timezone.utc)
        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="PLAN_RESUMED",
            actor=actor,
            details={"version": plan.version},
        )
        return True, "Plan successfully RESUMED."

    def cancel_plan(self, plan_id: str, actor: str, reason: str = "Operator cancellation.") -> tuple[bool, str]:
        """Cancel an active plan."""
        plan = self.get_plan(plan_id)
        if not plan:
            return False, f"Plan '{plan_id}' not found."

        plan.status = PlanStatus.CANCELLED
        plan.updated_at = datetime.now(timezone.utc)
        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="PLAN_CANCELLED",
            actor=actor,
            details={"reason": reason},
        )
        return True, "Plan successfully CANCELLED."

    def replan(
        self,
        plan_id: str,
        actor: str,
        reason: str,
        new_tasks: list[dict[str, Any]] | None = None,
    ) -> StrategicPlan:
        """Create a new plan revision preserving history without silent mutation.

        INVARIANT 15: Replanning preserves history.
        """
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        # Snapshot current version before revision
        revision = plan_lifecycle_manager.create_revision(
            plan=plan,
            reason=reason,
            actor=actor,
            diff_summary={"reason": reason, "previous_status": plan.status.value},
        )
        self._revisions.setdefault(plan.plan_id, []).append(revision)

        # Apply adaptations
        plan.status = PlanStatus.REPLANNING
        plan.health = HealthStatus.REPLANNING_REQUIRED
        plan.status = PlanStatus.READY  # Ready for resumed execution post adaptation

        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="REPLAN_COMPLETED",
            actor=actor,
            details={"new_version": plan.version, "revision_id": revision.revision_id, "reason": reason},
        )
        return plan

    def get_progress(self, plan_id: str) -> dict[str, Any]:
        """Get holistic progress metrics."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": f"Plan '{plan_id}' not found."}
        return progress_tracker.compute_plan_progress(plan)

    def get_timeline(self, plan_id: str) -> dict[str, Any]:
        """Get execution waves and schedule timeline."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": f"Plan '{plan_id}' not found."}

        cpm = critical_path_engine.compute_critical_path(plan.tasks)
        return {
            "plan_id": plan.plan_id,
            "created_at": plan.created_at.isoformat(),
            "deadline": plan.deadline.isoformat() if plan.deadline else None,
            "total_waves": len(plan.execution_waves),
            "waves": [w.model_dump() for w in plan.execution_waves],
            "critical_path": cpm,
        }

    def get_dependencies(self, plan_id: str) -> dict[str, Any]:
        """Get task dependency graph adjacency."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": f"Plan '{plan_id}' not found."}

        successors, predecessors = dependency_graph_engine.build_adjacency(plan.tasks)
        cycle = dependency_graph_engine.detect_cycles(plan.tasks)
        return {
            "plan_id": plan.plan_id,
            "has_cycle": len(cycle) > 0,
            "cycle_path": cycle,
            "successors": successors,
            "predecessors": predecessors,
            "tasks": [{"id": t.task_id, "title": t.title, "status": t.status} for t in plan.tasks],
        }

    def get_risks(self, plan_id: str) -> dict[str, Any]:
        """Get plan risks, propagations, and rollback steps."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": f"Plan '{plan_id}' not found."}

        rollback = plan_risk_engine.generate_rollback_strategy(plan.tasks)
        return {
            "plan_id": plan.plan_id,
            "risks": [r.model_dump() for r in plan.risks],
            "rollback_strategy": rollback,
        }

    def get_outcomes(self, plan_id: str) -> list[dict[str, Any]]:
        """Get recorded outcomes for the plan."""
        return [o.model_dump() for o in self._outcomes.get(plan_id, [])]

    def record_outcome(
        self,
        plan_id: str,
        success: bool,
        actual_duration_hours: float,
        actual_cost: float = 0.0,
        lessons_learned: list[str] | None = None,
    ) -> PlanOutcome:
        """Record plan outcome and learn from execution."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        outcome = outcome_tracker.record_plan_outcome(
            plan=plan,
            success=success,
            actual_duration_hours=actual_duration_hours,
            actual_cost=actual_cost,
            lessons_learned=lessons_learned,
        )
        self._outcomes.setdefault(plan_id, []).append(outcome)
        plan.status = PlanStatus.COMPLETED if success else PlanStatus.FAILED
        plan_auditor.record_event(
            plan_id=plan.plan_id,
            event_type="PLAN_COMPLETED" if success else "PLAN_FAILED",
            actor="OUTCOME_TRACKER",
            details={"success": success, "actual_duration": actual_duration_hours},
        )
        return outcome

    def get_audit_trail(self, plan_id: str) -> list[dict[str, Any]]:
        """Retrieve audit history for plan."""
        return plan_auditor.get_plan_events(plan_id)


planning_service = PlanningService()
