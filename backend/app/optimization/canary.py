"""Phased canary rollout controller and blast radius containment (Task 62)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.optimization.safety import (
    OptimizationSafetyError,
    optimization_kill_switch,
)
from app.optimization.schemas import (
    CanaryDeployment,
    ChangeSet,
    ChangeSetStatus,
    RolloutState,
)

logger = logging.getLogger(__name__)


class CanaryController:
    """Controls staged progressive rollout (0% -> 10% -> 50% -> 100%) with continuous health gates.

    Invariant 21: A canary is NOT equivalent to production-wide success. Rollout proceeds
    only when canary health criteria and verification gates pass.
    """

    def __init__(self) -> None:
        self._canaries: dict[str, CanaryDeployment] = {}

    def initiate_canary(
        self,
        change_set: ChangeSet,
        initial_traffic_pct: float = 10.0,
    ) -> CanaryDeployment:
        """Start a canary deployment for an approved change set."""
        optimization_kill_switch.check_active()

        if change_set.status != ChangeSetStatus.APPROVED:
            raise OptimizationSafetyError(
                f"Cannot initiate canary for change set in status '{change_set.status.value}'. Must be APPROVED."
            )

        canary = CanaryDeployment(
            change_set_id=change_set.change_set_id,
            rollout_state=RolloutState.CANARY_10 if initial_traffic_pct <= 10.0 else RolloutState.CANARY_50,
            traffic_percentage=initial_traffic_pct,
            blast_radius_scope="canary_partition",
            is_verified=False,
            failure_threshold_reached=False,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        change_set.status = ChangeSetStatus.APPLYING
        self._canaries[canary.canary_id] = canary
        logger.info(
            "CANARY_INITIATED: canary=%s change_set=%s traffic=%.1f%%",
            canary.canary_id,
            change_set.change_set_id,
            initial_traffic_pct,
        )
        return canary

    def advance_rollout(
        self,
        canary_id: str,
        target_state: RolloutState,
        is_verified: bool = True,
    ) -> CanaryDeployment:
        """Advance canary to next rollout stage after verification."""
        optimization_kill_switch.check_active()

        canary = self._canaries.get(canary_id)
        if not canary:
            raise OptimizationSafetyError(f"Canary deployment '{canary_id}' not found.")

        if canary.failure_threshold_reached:
            raise OptimizationSafetyError(
                f"Cannot advance canary '{canary_id}': failure threshold was reached."
            )

        if not is_verified:
            raise OptimizationSafetyError(
                f"Cannot advance canary '{canary_id}' without verified healthy telemetry."
            )

        canary.rollout_state = target_state
        canary.is_verified = True
        canary.updated_at = datetime.now(timezone.utc)

        if target_state == RolloutState.CANARY_50:
            canary.traffic_percentage = 50.0
        elif target_state == RolloutState.FULL_ROLLOUT:
            canary.traffic_percentage = 100.0

        logger.info(
            "CANARY_ADVANCED: canary=%s state=%s traffic=%.1f%%",
            canary_id,
            target_state.value,
            canary.traffic_percentage,
        )
        return canary

    def trigger_abort(self, canary_id: str, reason: str) -> CanaryDeployment:
        """Abort canary due to observed degradation or gate breach."""
        canary = self._canaries.get(canary_id)
        if not canary:
            raise OptimizationSafetyError(f"Canary deployment '{canary_id}' not found.")

        canary.rollout_state = RolloutState.ROLLED_BACK
        canary.failure_threshold_reached = True
        canary.traffic_percentage = 0.0
        canary.updated_at = datetime.now(timezone.utc)
        logger.warning(
            "CANARY_ABORTED: canary=%s reason='%s'",
            canary_id,
            reason,
        )
        return canary

    def get_canary(self, canary_id: str) -> CanaryDeployment | None:
        """Retrieve canary deployment by ID."""
        return self._canaries.get(canary_id)


canary_controller = CanaryController()
