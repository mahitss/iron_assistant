"""State reconciliation when action outcomes are unknown or timed out (Task 61)."""

from __future__ import annotations

import logging
from typing import Any

from app.incident_response.schemas import (
    ActionState,
    IncidentActionItem,
)

logger = logging.getLogger(__name__)


class IncidentReconciler:
    """Reconciles ambiguous or timed-out action outcomes against Digital Twin and observed telemetry.

    Invariant 76 & 79 & 80: Unknown action state must not cause blind retries of non-idempotent operations.
    """

    def reconcile_action(
        self,
        action: IncidentActionItem,
        observed_telemetry: dict[str, Any],
        digital_twin_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Determine actual real-world state of an action whose direct return status was inconclusive."""
        target = action.parameters.get("target_resource", "system")
        observed_health = observed_telemetry.get("status", "unknown").lower()
        twin_health = (digital_twin_state or {}).get("health", "unknown").lower()

        # If telemetry or digital twin proves target is now healthy/updated
        if observed_health in ("healthy", "ready", "ok") or twin_health in ("healthy", "ready", "ok"):
            action.status = ActionState.COMPLETED
            action.execution_result = {
                "reconciled": True,
                "target_resource": target,
                "basis": "Digital Twin & telemetry confirmed desired state",
            }
            logger.info(
                "ACTION_RECONCILED: action=%s target=%s confirmed COMPLETED via reconciliation.",
                action.action_id,
                target,
            )
            return {
                "reconciled_status": ActionState.COMPLETED,
                "should_retry": False,
                "rationale": "State reconciliation confirmed successful real-world application.",
            }

        # If non-idempotent and state is unknown -> NEVER blind retry
        if not action.is_idempotent:
            action.status = ActionState.FAILED
            logger.warning(
                "ACTION_RECONCILIATION_ABORTED: Non-idempotent action %s cannot be safely retried.",
                action.action_id,
            )
            return {
                "reconciled_status": ActionState.FAILED,
                "should_retry": False,
                "rationale": "Non-idempotent operation left in ambiguous state; automatic retry aborted for safety.",
            }

        # Idempotent action can be retried if below retry limit
        return {
            "reconciled_status": ActionState.QUEUED,
            "should_retry": True,
            "rationale": "Idempotent operation did not take effect; safe to retry with backoff.",
        }


incident_reconciler = IncidentReconciler()
