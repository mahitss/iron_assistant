"""Immutable versioned change sets and structured diff tracking (Task 62)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.optimization.safety import (
    OptimizationSafetyError,
    optimization_kill_switch,
)
from app.optimization.schemas import (
    ChangeSet,
    ChangeSetStatus,
    OptimizationRecommendation,
)

logger = logging.getLogger(__name__)


class ChangeSetManager:
    """Manages immutable, versioned change sets with structured before/after diffs.

    Invariant 19 & 44: Never silently mutate configuration. Every adaptive modification
    must be represented as a discrete, versioned change set with diff, risk, and rollback plan.
    """

    def __init__(self) -> None:
        self._change_sets: dict[str, ChangeSet] = {}

    def create_change_set(
        self,
        recommendation: OptimizationRecommendation,
        actor: str = "OPTIMIZER",
    ) -> ChangeSet:
        """Create a versioned change set from an optimization recommendation."""
        optimization_kill_switch.check_active()

        diff = {
            "parameter": recommendation.target_parameter,
            "before": recommendation.current_value,
            "after": recommendation.proposed_value,
            "delta": round(recommendation.proposed_value - recommendation.current_value, 4),
        }

        cs = ChangeSet(
            version=1,
            target_parameter=recommendation.target_parameter,
            before_state=recommendation.current_value,
            after_state=recommendation.proposed_value,
            diff=diff,
            reason=recommendation.title,
            risk=recommendation.risk,
            status=ChangeSetStatus.PROPOSED if recommendation.requires_approval else ChangeSetStatus.APPROVED,
            rollback_strategy=recommendation.rollback_strategy,
            created_at=datetime.now(timezone.utc),
        )
        self._change_sets[cs.change_set_id] = cs
        logger.info(
            "CHANGE_SET_CREATED: %s target=%s (%.2f -> %.2f) status=%s",
            cs.change_set_id,
            cs.target_parameter,
            cs.before_state,
            cs.after_state,
            cs.status.value,
        )
        return cs

    def get_change_set(self, change_set_id: str) -> ChangeSet | None:
        """Retrieve change set by ID."""
        return self._change_sets.get(change_set_id)

    def list_change_sets(self, status: ChangeSetStatus | None = None) -> list[ChangeSet]:
        """List tracked change sets."""
        if status:
            return [c for c in self._change_sets.values() if c.status == status]
        return list(self._change_sets.values())

    def approve_change_set(
        self,
        change_set_id: str,
        approver: str,
        approval_id: str | None = None,
    ) -> ChangeSet:
        """Record explicit human or policy approval for a change set."""
        optimization_kill_switch.check_active()
        cs = self._change_sets.get(change_set_id)
        if not cs:
            raise OptimizationSafetyError(f"Change set '{change_set_id}' not found.")
        if cs.status != ChangeSetStatus.PROPOSED:
            raise OptimizationSafetyError(f"Cannot approve change set in status '{cs.status.value}'.")

        cs.status = ChangeSetStatus.APPROVED
        cs.approver = approver
        cs.approval_id = approval_id or f"appr_{change_set_id[:8]}"
        logger.info("CHANGE_SET_APPROVED: %s by %s", change_set_id, approver)
        return cs


change_set_manager = ChangeSetManager()
