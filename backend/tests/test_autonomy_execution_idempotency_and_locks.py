"""Tests for Canonical Execution Loop, Idempotency Keys, Unknown Outcome Handling, and Resource Locking (Task 45)."""

import pytest
from app.autonomy.budgets import AutonomousBudget
from app.autonomy.checkpoints import CheckpointManager
from app.autonomy.controller import RunController
from app.autonomy.deadlines import DeadlineTracker
from app.autonomy.execution import (
    AutonomousExecutionLoop,
    ExecutionResourceManager,
    ResourceLockConflictError,
    SideEffectRetryViolationError,
)
from app.autonomy.interruption import InterruptionHandler
from app.autonomy.progress import ProgressTracker
from app.autonomy.safety import AutonomyLevel


def test_resource_manager_read_write_locks():
    """Verify reader-writer locking: concurrent reads allowed, conflicting writes blocked (Spec 33, 34)."""
    rm = ExecutionResourceManager()
    res = "data/config.json"

    # Step 1 acquires read lock
    assert rm.acquire_lock(res, step_id="step_read_1", is_write=False) is True
    # Step 2 acquires concurrent read lock
    assert rm.acquire_lock(res, step_id="step_read_2", is_write=False) is True

    # Step 3 attempts write lock while readers active -> ResourceLockConflictError
    with pytest.raises(ResourceLockConflictError):
        rm.acquire_lock(res, step_id="step_write_3", is_write=True)

    # Release readers
    rm.release_lock(res, "step_read_1")
    rm.release_lock(res, "step_read_2")

    # Now write lock succeeds
    assert rm.acquire_lock(res, step_id="step_write_3", is_write=True) is True

    # Another writer is blocked
    with pytest.raises(ResourceLockConflictError):
        rm.acquire_lock(res, step_id="step_write_4", is_write=True)

    rm.release_lock(res, "step_write_3")


def test_execution_loop_idempotency():
    """Verify idempotency key generation and cached replay without redundant side effects (Spec 46, 47)."""
    cm = CheckpointManager()
    pt = ProgressTracker()
    ih = InterruptionHandler()
    dt = DeadlineTracker()
    b = AutonomousBudget()

    ctrl = RunController(cm, pt, ih, dt, b, autonomy_level=AutonomyLevel.AUTONOMOUS)
    loop = AutonomousExecutionLoop(controller=ctrl)

    call_count = 0

    def mock_executor(tool_name: str, params: dict) -> dict:
        nonlocal call_count
        call_count += 1
        return {"result": "file created", "counter": call_count}

    step = {
        "step_id": "step_idemp_1",
        "action_type": "ANALYZE",
        "tool_name": "calc_tool",
        "params": {"query": "SELECT count(*) FROM users"},
        "is_idempotent": True,
    }

    # First execution calls tool
    res1 = loop.execute_step_safely("run_01", 1, step, mock_executor)
    assert res1.is_success is True
    assert call_count == 1

    # Second execution with same parameters hits idempotency cache!
    res2 = loop.execute_step_safely("run_01", 1, step, mock_executor)
    assert res2.is_success is True
    assert "Idempotent replay" in res2.verification_notes
    assert call_count == 1  # Tool was NOT called again


def test_unknown_outcome_and_non_idempotent_retry_safety():
    """Verify that non-idempotent operations cannot be retried blindly after failure without verification (Spec 43-45)."""
    cm = CheckpointManager()
    pt = ProgressTracker()
    ih = InterruptionHandler()
    dt = DeadlineTracker()
    b = AutonomousBudget()

    ctrl = RunController(cm, pt, ih, dt, b, autonomy_level=AutonomyLevel.AUTONOMOUS)
    loop = AutonomousExecutionLoop(controller=ctrl, max_retries_per_step=3)

    def failing_executor(tool_name: str, params: dict):
        raise TimeoutError("Network connection dropped during payment submission.")

    step = {
        "step_id": "step_pay_1",
        "action_type": "WRITE",
        "tool_name": "charge_customer",
        "params": {"amount": 100},
        "target_resource": "billing/account_123",
        "is_idempotent": False,  # Non-idempotent destructive operation!
    }

    # First execution fails due to network drop (caught and returned as unverified failure)
    res1 = loop.execute_step_safely("run_01", 1, step, failing_executor)
    assert res1.is_success is False
    assert "Network connection dropped" in (res1.error or "")

    # Subsequent retry WITHOUT state verification must be blocked!
    with pytest.raises(SideEffectRetryViolationError, match="Cannot blindly retry non-idempotent step"):
        loop.execute_step_safely("run_01", 1, step, failing_executor, state_inspector_fn=None)

    # But if state inspection proves payment already took effect, unknown outcome is safely recovered:
    def verify_payment_succeeded(res: str, params: dict) -> bool:
        return True  # Verified the charge occurred in payment gateway

    recovered = loop.execute_step_safely("run_01", 1, step, failing_executor, state_inspector_fn=verify_payment_succeeded)
    assert recovered.is_success is True
    assert recovered.outputs.get("recovered_prior_effect") is True


def test_dry_run_simulation_mode():
    """Verify that dry-run mode executes zero real side effects and clearly labels simulations (Spec 132, 133)."""
    cm = CheckpointManager()
    pt = ProgressTracker()
    ih = InterruptionHandler()
    dt = DeadlineTracker()
    b = AutonomousBudget()

    ctrl = RunController(cm, pt, ih, dt, b, autonomy_level=AutonomyLevel.AUTONOMOUS)
    dry_loop = AutonomousExecutionLoop(controller=ctrl, is_dry_run=True)

    executed = False

    def real_executor(tool: str, params: dict):
        nonlocal executed
        executed = True
        return {"mutated": True}

    step = {
        "step_id": "step_deploy_prod",
        "action_type": "DEPLOY",
        "tool_name": "deploy_prod",
        "params": {"version": "v2.0"},
    }

    res = dry_loop.execute_step_safely("run_dry_01", 1, step, real_executor)
    assert res.is_success is True
    assert executed is False  # Real executor NEVER invoked!
    assert res.outputs.get("dry_run") is True
    assert "Dry run simulation" in res.verification_notes
