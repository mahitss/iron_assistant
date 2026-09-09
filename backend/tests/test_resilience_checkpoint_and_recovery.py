"""Tests for checkpoints, corruption detection, and crash recovery with No Blind Resume."""

import pytest

from app.resilience.checkpoint import ResilienceCheckpointManager
from app.resilience.leases import LeaseManager
from app.resilience.recovery import TaskRecoveryManager
from app.resilience.schemas import RecoveryState
from app.resilience.watchdog import QuarantineManager


@pytest.mark.asyncio
async def test_checkpoint_sanitization_and_versioning():
    """Verifies checkpoints increment version numbers and strip sensitive credentials."""
    ckpt_mgr = ResilienceCheckpointManager()
    task_id = "task_backup_42"

    raw_state_1 = {
        "step": "step_1_init",
        "api_key": "sk-proj-secret123",
        "progress": 0.25,
    }
    ckpt1 = await ckpt_mgr.save_checkpoint(task_id, raw_state_1, step_id="step_1", policy_version=1)
    assert ckpt1.version == 1
    assert ckpt1.state_json["api_key"] == "[REDACTED]"
    assert ckpt1.state_json["progress"] == 0.25

    raw_state_2 = {
        "step": "step_2_fetch",
        "progress": 0.50,
    }
    ckpt2 = await ckpt_mgr.save_checkpoint(task_id, raw_state_2, step_id="step_2", policy_version=1)
    assert ckpt2.version == 2

    # Latest checkpoint returns v2
    latest = await ckpt_mgr.get_latest_valid_checkpoint(task_id)
    assert latest.version == 2
    assert latest.step_id == "step_2"


@pytest.mark.asyncio
async def test_checkpoint_corruption_fallback():
    """Verifies that a corrupt checkpoint causes fallback to the preceding valid checkpoint."""
    ckpt_mgr = ResilienceCheckpointManager()
    task_id = "task_corrupt_test"

    # Save valid checkpoint 1
    ckpt1 = await ckpt_mgr.save_checkpoint(task_id, {"step": "step_1", "ok": True}, step_id="step_1")

    # Save checkpoint 2
    ckpt2 = await ckpt_mgr.save_checkpoint(task_id, {"step": "step_2", "ok": True}, step_id="step_2")

    # Invalidate checkpoint 2 (simulate corruption)
    await ckpt_mgr.invalidate_checkpoint(ckpt2.id)

    # Latest valid checkpoint should now fall back to checkpoint 1!
    recovered_ckpt = await ckpt_mgr.get_latest_valid_checkpoint(task_id)
    assert recovered_ckpt is not None
    assert recovered_ckpt.id == ckpt1.id
    assert recovered_ckpt.step_id == "step_1"


@pytest.mark.asyncio
async def test_recovery_manager_no_blind_resume():
    """Verifies that TaskRecoveryManager strictly revalidates all safety conditions before resuming."""
    ckpt_mgr = ResilienceCheckpointManager()
    lease_mgr = LeaseManager()
    quarantine_mgr = QuarantineManager()
    recovery_mgr = TaskRecoveryManager(
        checkpoint_mgr=ckpt_mgr,
        lease_mgr=lease_mgr,
        quarantine_mgr=quarantine_mgr,
    )

    task_id = "task_prod_deploy"
    await ckpt_mgr.save_checkpoint(task_id, {"step": "step_3"}, step_id="step_3", policy_version=1)

    # 1. Quarantined task -> denied
    await quarantine_mgr.quarantine_task(task_id, reason="Poison task crash")
    state, _ = await recovery_mgr.evaluate_and_recover(task_id, "worker_recover", current_policy_version=1)
    assert state == RecoveryState.QUARANTINED
    await quarantine_mgr.release_task(task_id)

    # 2. Emergency stop active -> BLOCKED
    state, _ = await recovery_mgr.evaluate_and_recover(
        task_id, "worker_recover", current_policy_version=1, is_emergency_stopped=True
    )
    assert state == RecoveryState.BLOCKED

    # 3. User authorization revoked -> BLOCKED
    state, _ = await recovery_mgr.evaluate_and_recover(
        task_id, "worker_recover", current_policy_version=1, is_user_authorized=False
    )
    assert state == RecoveryState.BLOCKED

    # 4. Approvals expired -> WAITING_USER (cannot execute blindly)
    state, _ = await recovery_mgr.evaluate_and_recover(
        task_id, "worker_recover", current_policy_version=1, is_approval_valid=False
    )
    assert state == RecoveryState.WAITING_USER

    # 5. Target device disconnected -> WAITING_DEVICE
    state, _ = await recovery_mgr.evaluate_and_recover(
        task_id, "worker_recover", current_policy_version=1, is_device_connected=False
    )
    assert state == RecoveryState.WAITING_DEVICE

    # 6. Target resource stale/deleted -> FAILED
    state, _ = await recovery_mgr.evaluate_and_recover(
        task_id, "worker_recover", current_policy_version=1, is_target_fresh=False
    )
    assert state == RecoveryState.FAILED

    # 7. ALL CHECKS PASS -> RESUMABLE!
    state, recovered_ckpt = await recovery_mgr.evaluate_and_recover(
        task_id,
        "worker_recover",
        current_policy_version=1,
        is_emergency_stopped=False,
        is_approval_valid=True,
        is_device_connected=True,
        is_target_fresh=True,
        is_user_authorized=True,
    )
    assert state == RecoveryState.RESUMABLE
    assert recovered_ckpt.step_id == "step_3"


def test_deterministic_state_transitions():
    """Verifies that invalid state transitions are rejected."""
    mgr = TaskRecoveryManager()

    # Valid transitions
    assert mgr.validate_transition(RecoveryState.RECOVERING, RecoveryState.RESUMABLE) is True
    assert mgr.validate_transition(RecoveryState.RECOVERING, RecoveryState.WAITING_USER) is True
    assert mgr.validate_transition(RecoveryState.RESUMABLE, RecoveryState.COMPLETED) is True

    # Invalid transitions (cannot jump arbitrarily)
    assert mgr.validate_transition(RecoveryState.COMPLETED, RecoveryState.RECOVERING) is False
    assert mgr.validate_transition(RecoveryState.FAILED, RecoveryState.RESUMABLE) is False
    assert mgr.validate_transition(RecoveryState.CANCELLED, RecoveryState.RESUMABLE) is False
