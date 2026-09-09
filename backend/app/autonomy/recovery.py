"""Crash Recovery, Revalidation Pipeline, and Safe Resumption (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.autonomy.checkpoints import AutonomousCheckpoint, CheckpointManager
from app.autonomy.state import AutonomousRunState

logger = logging.getLogger("kairo.autonomy.recovery")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RecoveryRevalidationError(Exception):
    """Raised when an autonomous run fails pre-resumption security, authorization, or freshness revalidation."""


@dataclass
class StateRevalidationResult:
    """Outcome of pre-resumption state, plan, and authorization audit (Spec 16-19)."""

    is_valid: bool
    state_fresh: bool
    plan_valid: bool
    authorization_valid: bool
    approvals_valid: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class RecoveryDecision:
    """Prescribed recovery plan after crash, worker restart, or interruption (Spec 14, 27)."""

    run_id: str
    action: str  # RESUME, REPLAN, RETRY, PAUSE, FAIL
    checkpoint: AutonomousCheckpoint
    revalidation: StateRevalidationResult
    notes: str
    decided_at: datetime = field(default_factory=utc_now)


class RecoveryEngine:
    """Manages crash recovery without blind resumption (Specs 14-19, 106-110)."""

    def __init__(self, checkpoint_manager: CheckpointManager) -> None:
        self.checkpoint_manager = checkpoint_manager

    def revalidate_preconditions(
        self,
        checkpoint: AutonomousCheckpoint,
        current_world_state_version: Optional[str] = None,
        is_authorization_valid: bool = True,
        is_approval_expired: bool = False,
        plan_has_breaking_changes: bool = False,
    ) -> StateRevalidationResult:
        """Enforce Specs 15-19: Never blindly resume. Revalidate state, plan, and authorization."""
        reasons: List[str] = []
        state_fresh = True
        plan_valid = not plan_has_breaking_changes
        auth_valid = is_authorization_valid
        approvals_valid = not is_approval_expired

        # 1. State freshness check (Spec 16)
        if current_world_state_version and checkpoint.world_state_version:
            if current_world_state_version != checkpoint.world_state_version:
                state_fresh = False
                reasons.append(f"World state version changed ({checkpoint.world_state_version} -> {current_world_state_version}); reality has shifted.")

        # 2. Plan freshness check (Spec 17)
        if plan_has_breaking_changes:
            reasons.append("Plan dependencies or underlying tools were modified; requires replan.")

        # 3. Authorization check (Spec 19)
        if not auth_valid:
            reasons.append("User or project authorization has expired or was revoked.")

        # 4. Approval check (Spec 18)
        if is_approval_expired:
            reasons.append("Required external approval expired while paused; re-approval mandatory.")

        overall_valid = state_fresh and plan_valid and auth_valid and approvals_valid
        return StateRevalidationResult(
            is_valid=overall_valid,
            state_fresh=state_fresh,
            plan_valid=plan_valid,
            authorization_valid=auth_valid,
            approvals_valid=approvals_valid,
            reasons=reasons,
        )

    def plan_recovery(
        self,
        run_id: str,
        current_world_state_version: Optional[str] = None,
        is_authorization_valid: bool = True,
        is_approval_expired: bool = False,
        plan_has_breaking_changes: bool = False,
    ) -> RecoveryDecision:
        """Formulate a recovery plan from latest uncorrupted checkpoint (Spec 14, 27, 108)."""
        chk = self.checkpoint_manager.get_latest_valid_checkpoint(run_id)
        if not chk:
            raise RecoveryRevalidationError(f"Cannot recover run {run_id}: No valid checkpoint found.")

        reval = self.revalidate_preconditions(
            checkpoint=chk,
            current_world_state_version=current_world_state_version,
            is_authorization_valid=is_authorization_valid,
            is_approval_expired=is_approval_expired,
            plan_has_breaking_changes=plan_has_breaking_changes,
        )

        # Decision matrix
        if not reval.authorization_valid:
            action = "FAIL"
            notes = "Authorization invalid; cannot resume run."
        elif not reval.approvals_valid:
            action = "PAUSE"
            notes = "Approvals expired; paused waiting for fresh human approval."
        elif not reval.state_fresh or not reval.plan_valid:
            action = "REPLAN"
            notes = "State shifted or plan invalidated; triggering adaptive replanning."
        else:
            action = "RESUME"
            notes = f"Preconditions verified clean; resuming from step {chk.step_id or 'start'} at plan v{chk.plan_version}."

        logger.info("Recovery decision for run %s: %s (%s)", run_id, action, notes)
        return RecoveryDecision(
            run_id=run_id,
            action=action,
            checkpoint=chk,
            revalidation=reval,
            notes=notes,
        )
