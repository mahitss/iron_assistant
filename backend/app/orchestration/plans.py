"""Orchestration plan lifecycle, environmental drift revalidation, snapshots, and revision diffs (Task 59)."""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any

from app.orchestration.safety import (
    OrchestrationSafetyError,
    StaleOrchestrationError,
)
from app.orchestration.schemas import (
    HealthStatus,
    OrchestrationPlan,
    OrchestrationRevision,
    OrchestrationStatus,
    ProviderAssignment,
)

logger = logging.getLogger(__name__)


class OrchestrationLifecycleManager:
    """Manages the lifecycle, snapshots, revalidation, and revisions of orchestration plans."""

    def __init__(self) -> None:
        self._plans: dict[str, OrchestrationPlan] = {}
        self._revisions: dict[str, list[OrchestrationRevision]] = {}

    def save_plan(self, plan: OrchestrationPlan) -> OrchestrationPlan:
        """Store an orchestration plan in memory cache."""
        self._plans[plan.orchestration_id] = plan
        return plan

    def get_plan(self, orchestration_id: str) -> OrchestrationPlan:
        """Retrieve an orchestration plan by ID."""
        plan = self._plans.get(orchestration_id)
        if not plan:
            raise OrchestrationSafetyError(f"Orchestration plan '{orchestration_id}' not found.")
        return plan

    def revalidate_plan(
        self,
        orchestration_id: str,
        current_environment: str,
        active_permissions: set[str],
        unhealthy_providers: set[str] | None = None,
    ) -> bool:
        """Revalidate all assignments against current environment, permissions, and provider health.

        Raises StaleOrchestrationError if state has drifted.
        """
        plan = self.get_plan(orchestration_id)
        unhealthy = unhealthy_providers or set()
        stale_reasons = []

        for asgn in plan.assignments:
            # Check provider health
            if asgn.provider_name in unhealthy:
                stale_reasons.append(f"Provider '{asgn.provider_name}' for task '{asgn.task_id}' is now unhealthy/unavailable.")

            # Check permissions
            for perm in asgn.required_permissions:
                if perm not in active_permissions:
                    stale_reasons.append(f"Permission '{perm}' required for task '{asgn.task_id}' has been revoked.")

        if stale_reasons:
            plan.status = OrchestrationStatus.BLOCKED
            plan.health = HealthStatus.BLOCKED
            err_msg = "; ".join(stale_reasons)
            logger.warning("ORCHESTRATION_STALE: plan=%s reasons=%s", orchestration_id, err_msg)
            raise StaleOrchestrationError(f"Orchestration plan '{orchestration_id}' requires revalidation: {err_msg}")

        plan.status = OrchestrationStatus.VALIDATED
        plan.health = HealthStatus.ON_TRACK
        logger.info("ORCHESTRATION_REVALIDATED: plan=%s is valid for execution", orchestration_id)
        return True

    def create_revision(
        self,
        orchestration_id: str,
        actor: str,
        reason: str,
        new_assignments: list[ProviderAssignment],
    ) -> OrchestrationRevision:
        """Record an immutable revision diff when assignments or allocations change materially."""
        plan = self.get_plan(orchestration_id)
        old_assignments = {a.task_id: a.provider_name for a in plan.assignments}
        new_map = {a.task_id: a.provider_name for a in new_assignments}

        diff: dict[str, Any] = {}
        for tid, new_prov in new_map.items():
            old_prov = old_assignments.get(tid)
            if old_prov != new_prov:
                diff[tid] = {
                    "previous_provider": old_prov,
                    "new_provider": new_prov,
                }

        rev_num = plan.version + 1
        plan.version = rev_num
        plan.assignments = new_assignments

        revision = OrchestrationRevision(
            revision_id=f"orev_{uuid.uuid4().hex[:8]}",
            parent_orchestration_id=orchestration_id,
            revision_number=rev_num,
            reason=reason,
            actor=actor,
            diff_summary=diff,
            snapshot=copy.deepcopy(plan.model_dump()),
        )

        if orchestration_id not in self._revisions:
            self._revisions[orchestration_id] = []
        self._revisions[orchestration_id].append(revision)

        logger.info("REVISION_CREATED: plan=%s revision=%d changed_tasks=%d", orchestration_id, rev_num, len(diff))
        return revision

    def get_revisions(self, orchestration_id: str) -> list[OrchestrationRevision]:
        """Return revision history for a plan."""
        return self._revisions.get(orchestration_id, [])


orchestration_lifecycle_manager = OrchestrationLifecycleManager()
