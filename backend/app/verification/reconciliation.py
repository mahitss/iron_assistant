"""State Reconciliation Engine for Kairo (Task 42).

Triggers reconciliation when verification reveals discrepancies between
expected state and observed state. Enforces safety boundaries (never auto-repairs
ambiguous authoritative state, but allows repairing caches, derived state, and plan tasks).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.verification.assertions import VerificationResult, VerificationStatus

logger = logging.getLogger("kairo.verification.reconciliation")


@dataclass
class ReconciliationAction:
    """Action taken to reconcile a verified discrepancy."""

    action_id: str
    target_resource: str
    discrepancy: str
    resolution_type: str  # "CACHE_INVALIDATION", "DERIVED_STATE_SYNC", "TASK_STATUS_RESET", "ESCALATION_REQUIRED"
    auto_repaired: bool
    requires_human_review: bool
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "target_resource": self.target_resource,
            "discrepancy": self.discrepancy,
            "resolution_type": self.resolution_type,
            "auto_repaired": self.auto_repaired,
            "requires_human_review": self.requires_human_review,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }


class StateReconciler:
    """Coordinates discrepancy diagnosis and safe reconciliation triggers."""

    def __init__(self) -> None:
        self._history: list[ReconciliationAction] = []

    def reconcile(
        self,
        target_resource: str,
        verification_result: VerificationResult,
        resource_authority: str = "DERIVED",  # "AUTHORITATIVE" or "DERIVED"
    ) -> ReconciliationAction:
        """Trigger reconciliation for a failed or mismatched verification result."""
        action_id = f"rec-{uuid.uuid4().hex[:8]}"
        discrepancy_str = "; ".join(verification_result.discrepancies) or "Verification failure without explicit discrepancy"

        # Safety Check (Spec 134):
        # Do not auto-repair ambiguous authoritative state!
        if resource_authority == "AUTHORITATIVE":
            logger.warning(
                "Discrepancy detected in AUTHORITATIVE state for '%s'. Escalating for human review without auto-repair.",
                target_resource,
            )
            action = ReconciliationAction(
                action_id=action_id,
                target_resource=target_resource,
                discrepancy=discrepancy_str,
                resolution_type="ESCALATION_REQUIRED",
                auto_repaired=False,
                requires_human_review=True,
                details={
                    "verifier": verification_result.verifier,
                    "reason": "Authoritative state cannot be blindly auto-repaired.",
                },
            )
            self._history.append(action)
            return action

        # Derived state or cache safe auto-repair
        if "cache" in target_resource.lower() or "view" in target_resource.lower():
            resolution = "CACHE_INVALIDATION"
            auto_repaired = True
            requires_review = False
        elif "task" in target_resource.lower() or "step" in target_resource.lower():
            resolution = "TASK_STATUS_RESET"
            auto_repaired = True
            requires_review = False
        else:
            resolution = "DERIVED_STATE_SYNC"
            auto_repaired = True
            requires_review = False

        action = ReconciliationAction(
            action_id=action_id,
            target_resource=target_resource,
            discrepancy=discrepancy_str,
            resolution_type=resolution,
            auto_repaired=auto_repaired,
            requires_human_review=requires_review,
            details={"verifier": verification_result.verifier},
        )
        self._history.append(action)
        return action

    def get_history(self) -> list[ReconciliationAction]:
        """Return history of all reconciliation actions."""
        return list(self._history)
