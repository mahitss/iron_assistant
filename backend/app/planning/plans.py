"""Strategic plan lifecycle, immutable versioning, validation, and diffing (Task 58)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.planning.dependencies import dependency_graph_engine
from app.planning.resources import resource_manager
from app.planning.safety import DependencyCycleError
from app.planning.schemas import (
    HealthStatus,
    PlanRevision,
    StateCertainty,
    StrategicPlan,
)

logger = logging.getLogger(__name__)


class PlanValidationResult:
    def __init__(
        self,
        is_valid: bool,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        unknowns: list[str] | None = None,
        blocked_items: list[str] | None = None,
        missing_information: list[str] | None = None,
    ) -> None:
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.unknowns = unknowns or []
        self.blocked_items = blocked_items or []
        self.missing_information = missing_information or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "unknowns": self.unknowns,
            "blocked_items": self.blocked_items,
            "missing_information": self.missing_information,
        }


class PlanLifecycleManager:
    """Oversees plan lifecycle states, validation gates, historical revisions, and version diffs."""

    def validate_plan(
        self,
        plan: StrategicPlan,
        known_system_resources: dict[str, float] | None = None,
    ) -> PlanValidationResult:
        """Comprehensive validation of strategic plan prior to execution handoff.

        INVARIANT 18: Planning cannot bypass safety systems.
        """
        errors: list[str] = []
        warnings: list[str] = []
        unknowns: list[str] = []
        blocked: list[str] = []
        missing_info: list[str] = []

        # 1. State Freshness & Certainty
        if plan.current_state.certainty == StateCertainty.STALE or plan.current_state.is_stale:
            errors.append("Current state assessment is STALE. Revalidation against Digital Twin required.")
        elif plan.current_state.certainty == StateCertainty.UNKNOWN:
            unknowns.append("Current state certainty is marked UNKNOWN.")

        # 2. Desired State Invariants
        if not plan.desired_state.completion_invariants and not plan.desired_state.verification_criteria:
            warnings.append("Desired state lacks explicit completion invariants or verification criteria.")

        # 3. Dependency Validation & Cycle Detection
        deps_valid, dep_errors = dependency_graph_engine.validate_dependencies(plan.tasks)
        if not deps_valid:
            errors.extend(dep_errors)

        try:
            cycle = dependency_graph_engine.detect_cycles(plan.tasks)
            if cycle:
                errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
        except DependencyCycleError as e:
            errors.append(str(e))

        # 4. Resource Allocation & Non-Fabrication
        res_ok, res_issues = resource_manager.validate_resource_availability(
            plan.tasks, known_system_resources=known_system_resources
        )
        if not res_ok:
            for issue in res_issues:
                if "UNKNOWN" in issue:
                    unknowns.append(issue)
                else:
                    errors.append(issue)

        # 5. Check for Orphan Tasks or Unassigned Owners
        for t in plan.tasks:
            if t.owner == "OWNER_UNASSIGNED":
                warnings.append(f"Task '{t.title}' has no assigned owner (OWNER_UNASSIGNED).")
            if not t.verification_criteria:
                warnings.append(f"Task '{t.title}' has no verification criteria.")

        is_valid = len(errors) == 0
        return PlanValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            unknowns=unknowns,
            blocked_items=blocked,
            missing_information=missing_info,
        )

    def create_revision(
        self,
        plan: StrategicPlan,
        reason: str,
        actor: str,
        diff_summary: dict[str, Any] | None = None,
    ) -> PlanRevision:
        """Create an immutable snapshot revision prior to mutating plan state.

        INVARIANT 15: Replanning preserves history.
        """
        snapshot = plan.model_dump(mode="json")
        revision = PlanRevision(
            parent_plan_id=plan.plan_id,
            revision_number=plan.version,
            reason=reason,
            actor=actor,
            diff_summary=diff_summary or {},
            snapshot=snapshot,
        )
        plan.version += 1
        plan.updated_at = datetime.now(timezone.utc)
        logger.info(
            "Created revision %s for plan %s (now v%s) by %s.",
            revision.revision_id,
            plan.plan_id,
            plan.version,
            actor,
        )
        return revision

    def compute_plan_diff(
        self,
        old_plan: StrategicPlan,
        new_plan: StrategicPlan,
    ) -> dict[str, Any]:
        """Compute structured diff between two plan versions."""
        old_task_ids = {t.task_id: t for t in old_plan.tasks}
        new_task_ids = {t.task_id: t for t in new_plan.tasks}

        added_tasks = [t.title for tid, t in new_task_ids.items() if tid not in old_task_ids]
        removed_tasks = [t.title for tid, t in old_task_ids.items() if tid not in new_task_ids]
        modified_tasks: list[dict[str, Any]] = []

        for tid, n_task in new_task_ids.items():
            if tid in old_task_ids:
                o_task = old_task_ids[tid]
                changes: list[str] = []
                if o_task.status != n_task.status:
                    changes.append(f"status: {o_task.status} -> {n_task.status}")
                if o_task.duration_expected != n_task.duration_expected:
                    changes.append(f"duration: {o_task.duration_expected} -> {n_task.duration_expected}")
                if changes:
                    modified_tasks.append({"task_id": tid, "title": n_task.title, "changes": changes})

        return {
            "from_version": old_plan.version,
            "to_version": new_plan.version,
            "tasks_added": added_tasks,
            "tasks_removed": removed_tasks,
            "tasks_modified": modified_tasks,
            "strategy_changed": old_plan.strategy.strategy_id != new_plan.strategy.strategy_id,
        }

    def check_plan_freshness(self, plan: StrategicPlan, max_age_hours: float = 48.0) -> bool:
        """Verify plan freshness. Returns False if plan is stale or current state expired."""
        age_hours = (datetime.now(timezone.utc) - plan.updated_at).total_seconds() / 3600.0
        if age_hours > max_age_hours or plan.current_state.is_stale:
            plan.health = HealthStatus.STALE
            return False
        return True


plan_lifecycle_manager = PlanLifecycleManager()
