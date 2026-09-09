"""Tests for Durable Checkpoints, Integrity Hashing, Corruption Fallback, and Crash Recovery (Task 45)."""

import pytest
from app.autonomy.checkpoints import (
    AutonomousCheckpoint,
    CheckpointManager,
    CorruptCheckpointError,
)
from app.autonomy.recovery import (
    RecoveryDecision,
    RecoveryEngine,
    RecoveryRevalidationError,
    StateRevalidationResult,
)


def test_checkpoint_integrity_and_hashing():
    """Verify cryptographic SHA-256 integrity hashing of checkpoints (Spec 10, 11, 108)."""
    cm = CheckpointManager()
    run_id = "run_chk_01"

    chk = cm.create_checkpoint(
        run_id=run_id,
        plan_version=1,
        run_state="RUNNING",
        step_id="step_1",
        completed_work=[{"step_id": "step_1", "status": "done"}],
        world_state_version="v1.0",
    )
    assert chk.checkpoint_id.startswith("chk_")
    assert len(chk.corruption_hash) == 64
    assert chk.verify_integrity() is True

    # Tampering with checkpoint data invalidates integrity
    chk.completed_work.append({"step_id": "injected_step", "status": "forged"})
    assert chk.verify_integrity() is False


def test_checkpoint_corruption_fallback():
    """Verify fallback to previous valid checkpoint when latest is corrupt (Spec 108, 109)."""
    cm = CheckpointManager()
    run_id = "run_fallback_01"

    # 1. First valid checkpoint
    chk1 = cm.create_checkpoint(run_id=run_id, plan_version=1, run_state="RUNNING", step_id="step_1")
    # 2. Second valid checkpoint
    chk2 = cm.create_checkpoint(run_id=run_id, plan_version=1, run_state="RUNNING", step_id="step_2")

    latest = cm.get_latest_valid_checkpoint(run_id)
    assert latest.checkpoint_id == chk2.checkpoint_id

    # Corrupt latest checkpoint
    chk2.corruption_hash = "corrupted_fake_hash_000000000000000000000000000000000000000000"

    # Fallback retrieves chk1
    fallback = cm.get_latest_valid_checkpoint(run_id)
    assert fallback.checkpoint_id == chk1.checkpoint_id


def test_recovery_revalidation_pipeline():
    """Verify recovery decisions without blind resume (Spec 14-19, 27)."""
    cm = CheckpointManager()
    rec_engine = RecoveryEngine(cm)
    run_id = "run_rec_01"

    cm.create_checkpoint(
        run_id=run_id,
        plan_version=1,
        run_state="PAUSED",
        step_id="step_2",
        world_state_version="world_v1",
    )

    # 1. Clean revalidation -> RESUME
    dec_resume = rec_engine.plan_recovery(
        run_id=run_id,
        current_world_state_version="world_v1",
        is_authorization_valid=True,
        is_approval_expired=False,
        plan_has_breaking_changes=False,
    )
    assert dec_resume.action == "RESUME"
    assert dec_resume.revalidation.is_valid is True

    # 2. Shifted world state -> REPLAN (Spec 16)
    dec_replan = rec_engine.plan_recovery(
        run_id=run_id,
        current_world_state_version="world_v2_shifted",
        is_authorization_valid=True,
    )
    assert dec_replan.action == "REPLAN"
    assert dec_replan.revalidation.state_fresh is False

    # 3. Expired approvals -> PAUSE for human approval (Spec 18)
    dec_pause = rec_engine.plan_recovery(
        run_id=run_id,
        current_world_state_version="world_v1",
        is_approval_expired=True,
    )
    assert dec_pause.action == "PAUSE"
    assert dec_pause.revalidation.approvals_valid is False

    # 4. Revoked authorization -> FAIL (Spec 19)
    dec_fail = rec_engine.plan_recovery(
        run_id=run_id,
        current_world_state_version="world_v1",
        is_authorization_valid=False,
    )
    assert dec_fail.action == "FAIL"
    assert dec_fail.revalidation.authorization_valid is False
