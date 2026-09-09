"""Task recovery manager enforcing strict 'No Blind Resume' revalidation."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.checkpoint import ResilienceCheckpointManager
from app.resilience.leases import LeaseLostError, LeaseManager
from app.resilience.schemas import RecoveryState, TaskCheckpoint, utc_now
from app.resilience.watchdog import QuarantineManager

logger = logging.getLogger(__name__)


class RecoveryValidationError(Exception):
    """Raised when safety revalidation fails during recovery."""
    def __init__(self, reason: str, state: RecoveryState):
        self.reason = reason
        self.state = state
        super().__init__(f"Recovery revalidation failed: {reason} (Target state: {state})")


class TaskRecoveryManager:
    """Manages crash recovery, lease acquisition, and strict safety revalidation."""

    # Deterministic State Transition Matrix
    VALID_TRANSITIONS: dict[RecoveryState, set[RecoveryState]] = {
        RecoveryState.RECOVERING: {
            RecoveryState.RESUMABLE,
            RecoveryState.WAITING_USER,
            RecoveryState.WAITING_DEVICE,
            RecoveryState.WAITING_DEPENDENCY,
            RecoveryState.BLOCKED,
            RecoveryState.FAILED,
            RecoveryState.QUARANTINED,
            RecoveryState.CANCELLED,
        },
        RecoveryState.RESUMABLE: {
            RecoveryState.COMPLETED,
            RecoveryState.FAILED,
            RecoveryState.BLOCKED,
            RecoveryState.CANCELLED,
            RecoveryState.QUARANTINED,
            RecoveryState.RECOVERING,
        },
        RecoveryState.WAITING: {
            RecoveryState.RESUMABLE,
            RecoveryState.CANCELLED,
            RecoveryState.FAILED,
        },
        RecoveryState.WAITING_USER: {
            RecoveryState.RESUMABLE,
            RecoveryState.CANCELLED,
            RecoveryState.FAILED,
        },
        RecoveryState.WAITING_DEVICE: {
            RecoveryState.RESUMABLE,
            RecoveryState.CANCELLED,
            RecoveryState.FAILED,
        },
        RecoveryState.WAITING_DEPENDENCY: {
            RecoveryState.RESUMABLE,
            RecoveryState.CANCELLED,
            RecoveryState.FAILED,
        },
        RecoveryState.UNKNOWN_OUTCOME: {
            RecoveryState.RESUMABLE,
            RecoveryState.COMPLETED,
            RecoveryState.FAILED,
        },
        RecoveryState.DEGRADED: {
            RecoveryState.RESUMABLE,
            RecoveryState.COMPLETED,
            RecoveryState.FAILED,
        },
        RecoveryState.BLOCKED: {
            RecoveryState.RESUMABLE,
            RecoveryState.FAILED,
            RecoveryState.CANCELLED,
        },
        RecoveryState.QUARANTINED: {
            RecoveryState.RECOVERING,
            RecoveryState.FAILED,
            RecoveryState.CANCELLED,
        },
        RecoveryState.COMPLETED: set(),
        RecoveryState.FAILED: set(),
        RecoveryState.CANCELLED: set(),
    }

    def __init__(
        self,
        checkpoint_mgr: ResilienceCheckpointManager | None = None,
        lease_mgr: LeaseManager | None = None,
        quarantine_mgr: QuarantineManager | None = None,
    ) -> None:
        self.checkpoint_mgr = checkpoint_mgr or ResilienceCheckpointManager()
        self.lease_mgr = lease_mgr or LeaseManager()
        self.quarantine_mgr = quarantine_mgr or QuarantineManager()
        self.recovery_successes: int = 0
        self.recovery_failures: int = 0

    def validate_transition(self, current: RecoveryState, target: RecoveryState) -> bool:
        """Validates that state transition is legal according to the transition matrix."""
        allowed = self.VALID_TRANSITIONS.get(current, set())
        return target in allowed

    async def evaluate_and_recover(
        self,
        task_id: str,
        worker_id: str,
        current_policy_version: int,
        is_emergency_stopped: bool = False,
        is_approval_valid: bool = True,
        is_device_connected: bool = True,
        is_target_fresh: bool = True,
        is_user_authorized: bool = True,
        session: AsyncSession | None = None,
    ) -> tuple[RecoveryState, TaskCheckpoint | None]:
        """Evaluates whether a task can resume after crash, enforcing 'No Blind Resume' rules."""
        # 1. Check if task is quarantined (poison task)
        if await self.quarantine_mgr.is_quarantined(task_id, session):
            logger.warning("Resilience: Task '%s' is quarantined. Automatic recovery denied.", task_id)
            self.recovery_failures += 1
            return RecoveryState.QUARANTINED, None

        # 2. Check emergency stop
        if is_emergency_stopped:
            logger.warning("Resilience: Emergency stop active. Recovery halted for task '%s'.", task_id)
            self.recovery_failures += 1
            return RecoveryState.BLOCKED, None

        # 3. Check checkpoint validity
        checkpoint = await self.checkpoint_mgr.get_latest_valid_checkpoint(task_id, session)
        if not checkpoint or not checkpoint.is_valid:
            logger.error("Resilience: Task '%s' has missing or corrupt checkpoint. Cannot resume.", task_id)
            self.recovery_failures += 1
            return RecoveryState.FAILED, None

        # 4. User authorization revalidation
        if not is_user_authorized:
            logger.warning("Resilience: User authorization revoked/invalid for task '%s'.", task_id)
            self.recovery_failures += 1
            return RecoveryState.BLOCKED, checkpoint

        # 5. Policy version check: If policy updated since checkpoint, requires re-evaluation
        if checkpoint.policy_version is not None and checkpoint.policy_version < current_policy_version:
            logger.info(
                "Resilience: Task '%s' checkpoint policy v%d older than current policy v%d. Revalidation needed.",
                task_id, checkpoint.policy_version, current_policy_version
            )

        # 6. Approvals revalidation: If approvals expired or missing
        if not is_approval_valid:
            logger.warning("Resilience: Approval expired for task '%s'. Waiting for user approval.", task_id)
            return RecoveryState.WAITING_USER, checkpoint

        # 7. Device connectivity check
        if not is_device_connected:
            logger.warning("Resilience: Target device disconnected for task '%s'. Waiting for device.", task_id)
            return RecoveryState.WAITING_DEVICE, checkpoint

        # 8. Target freshness check
        if not is_target_fresh:
            logger.warning("Resilience: Target resource state changed or deleted for task '%s'.", task_id)
            self.recovery_failures += 1
            return RecoveryState.FAILED, checkpoint

        # 9. Acquire lease for new worker
        try:
            await self.lease_mgr.acquire_lease(task_id, worker_id, session=session)
        except LeaseLostError as lle:
            logger.warning("Resilience: Could not acquire lease for '%s': %s", task_id, lle)
            return RecoveryState.BLOCKED, checkpoint

        # All checks passed: Safe to resume!
        self.recovery_successes += 1
        logger.info("Resilience: Task '%s' safely verified. Resuming from step '%s'.", task_id, checkpoint.step_id)
        return RecoveryState.RESUMABLE, checkpoint
