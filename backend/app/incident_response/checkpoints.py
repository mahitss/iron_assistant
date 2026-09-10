"""Recovery checkpoint barriers, state revalidation, and anti-blind-recovery safeguards (Task 61)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.incident_response.schemas import (
    RecoveryCheckpoint,
    RecoveryPlan,
    RecoveryState,
)

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Enforces verification barriers between recovery steps and blocks blind execution if state drifts.

    Invariant 43-45: Recovery proceeds only when checkpoints pass; environment drift pauses the plan.
    """

    def verify_checkpoint(
        self,
        plan: RecoveryPlan,
        checkpoint_id: str,
        verification_evidence: dict[str, Any],
        environmental_drift: bool = False,
    ) -> tuple[bool, str]:
        """Validate that a recovery checkpoint has satisfied its verification barrier."""
        chk: RecoveryCheckpoint | None = None
        for c in plan.checkpoints:
            if c.checkpoint_id == checkpoint_id:
                chk = c
                break

        if not chk:
            return False, f"Checkpoint '{checkpoint_id}' not found in plan '{plan.plan_id}'."

        # Invariant 44 & 45: Anti-blind recovery check
        if environmental_drift:
            logger.warning(
                "CHECKPOINT_PAUSED: Environmental drift detected on incident %s. Pausing recovery.",
                plan.incident_id,
            )
            plan.status = RecoveryState.PARTIAL
            return False, "Environmental drift detected: recovery paused for revalidation."

        # Verification barrier check
        if not verification_evidence or not verification_evidence.get("is_verified", False):
            logger.warning("CHECKPOINT_FAILED: Verification failed on checkpoint %s.", checkpoint_id)
            return False, f"Verification criteria not satisfied: {chk.verification_criteria}"

        # Pass checkpoint
        chk.is_passed = True
        chk.verified_at = datetime.now(timezone.utc)
        chk.revalidation_state = verification_evidence

        # Advance step index
        if plan.current_step_index < len(plan.steps):
            plan.steps[plan.current_step_index].is_completed = True
            plan.current_step_index += 1

        all_passed = all(c.is_passed for c in plan.checkpoints)
        plan.status = RecoveryState.RECOVERED if all_passed else RecoveryState.IN_PROGRESS

        logger.info(
            "CHECKPOINT_PASSED: checkpoint=%s incident=%s step_progress=%d/%d",
            checkpoint_id,
            plan.incident_id,
            plan.current_step_index,
            len(plan.steps),
        )
        return True, "Checkpoint verified successfully."


checkpoint_manager = CheckpointManager()
