"""Tests for idempotency keys, duplicate execution prevention, and unknown outcome reconciliation."""

import asyncio
import pytest

from app.resilience.idempotency import ConcurrentExecutionError, IdempotencyManager
from app.resilience.manager import ResilienceManager
from app.resilience.reconciliation import OutcomeReconciler, UnknownOutcomeException
from app.resilience.schemas import OutcomeState, SideEffectType


def test_idempotency_key_generation():
    """Verifies deterministic, sanitized key generation without secrets."""
    key1 = IdempotencyManager.generate_key(
        operation="deploy_service",
        user_id="alice",
        task_id="task_123",
        step_id="step_1",
        target="cluster_prod",
    )
    key2 = IdempotencyManager.generate_key(
        operation="deploy_service",
        user_id="alice",
        task_id="task_123",
        step_id="step_1",
        target="cluster_prod",
    )
    key3 = IdempotencyManager.generate_key(
        operation="deploy_service",
        user_id="bob",  # Different user
        task_id="task_123",
        step_id="step_1",
        target="cluster_prod",
    )

    assert key1.startswith("idem_deploy_service_")
    assert key1 == key2  # Deterministic
    assert key1 != key3  # Isolated by user


@pytest.mark.asyncio
async def test_idempotency_duplicate_execution_returns_cached_result():
    """Verifies duplicate execution with same idempotency key executes the underlying side effect only once."""
    mgr = IdempotencyManager()
    key = "idem_charge_cust_abc"
    call_count = 0

    async def charge_card():
        nonlocal call_count
        call_count += 1
        return {"charge_id": "ch_999", "amount": 5000}

    # First execution
    is_new, rec = await mgr.begin_operation(key=key, operation="charge")
    assert is_new is True
    res1 = await charge_card()
    await mgr.complete_operation(key=key, result_reference=res1)

    # Second execution attempt with identical key
    is_new2, rec2 = await mgr.begin_operation(key=key, operation="charge")
    assert is_new2 is False
    assert rec2.status == "COMPLETED"
    assert rec2.result_reference == {"charge_id": "ch_999", "amount": 5000}
    assert call_count == 1  # Side effect executed only ONCE!


@pytest.mark.asyncio
async def test_idempotency_concurrent_execution_detected():
    """Verifies concurrent executions on the same idempotency key are rejected."""
    mgr = IdempotencyManager()
    key = "idem_concurrent_op_test"

    is_new, _ = await mgr.begin_operation(key=key, operation="create_vm")
    assert is_new is True

    # Second call while first is still STARTED
    with pytest.raises(ConcurrentExecutionError):
        await mgr.begin_operation(key=key, operation="create_vm")


@pytest.mark.asyncio
async def test_unknown_outcome_reconciliation_verifies_state_before_retry():
    """Verifies that an unknown outcome queries authoritative source and prevents duplicate actions."""
    # Scenario A: Server timed out, but authoritative check reveals SUCCESS -> DO NOT RETRY!
    async def verifier_success():
        return OutcomeState.SUCCESS, {"deploy_id": "d-123", "status": "deployed"}

    safe_to_retry = await OutcomeReconciler.verify_before_retry(
        operation="deploy_k8s",
        side_effect_started=True,
        verifier=verifier_success,
    )
    assert safe_to_retry is False  # Already succeeded! Duplicate deploy prevented.

    # Scenario B: Server timed out, authoritative check reveals FAILED -> SAFE TO RETRY
    async def verifier_failed():
        return OutcomeState.FAILED, {"error": "container crashed on init"}

    safe_to_retry = await OutcomeReconciler.verify_before_retry(
        operation="deploy_k8s",
        side_effect_started=True,
        verifier=verifier_failed,
    )
    assert safe_to_retry is True

    # Scenario C: Server timed out, authoritative check returns UNKNOWN -> BLIND RETRY BLOCKED!
    async def verifier_unknown():
        return OutcomeState.UNKNOWN, None

    safe_to_retry = await OutcomeReconciler.verify_before_retry(
        operation="deploy_k8s",
        side_effect_started=True,
        verifier=verifier_unknown,
    )
    assert safe_to_retry is False

    # Scenario D: Side effect never started (failed before dispatch) -> Safe to retry
    safe_to_retry = await OutcomeReconciler.verify_before_retry(
        operation="deploy_k8s",
        side_effect_started=False,
        verifier=None,
    )
    assert safe_to_retry is True


@pytest.mark.asyncio
async def test_resilience_manager_execute_resilient_operation():
    """Verifies end-to-end resilient execution wrapper with caching and timeout."""
    manager = ResilienceManager()
    invocations = 0

    async def mock_compute():
        nonlocal invocations
        invocations += 1
        return {"data": 42}

    key = "idem_comp_123"
    res1 = await manager.execute_resilient_operation(
        func=mock_compute,
        operation="compute_math",
        component="calc",
        side_effect_type=SideEffectType.IDEMPOTENT_WRITE,
        idempotency_key=key,
        timeout_seconds=5.0,
    )
    assert res1 == {"data": 42}
    assert invocations == 1

    # Re-run with same key -> returns cached result
    res2 = await manager.execute_resilient_operation(
        func=mock_compute,
        operation="compute_math",
        component="calc",
        side_effect_type=SideEffectType.IDEMPOTENT_WRITE,
        idempotency_key=key,
        timeout_seconds=5.0,
    )
    assert res2 == {"data": 42}
    assert invocations == 1  # Did not re-invoke!
