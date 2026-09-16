"""Comprehensive unit and invariant tests for Task 95: Execution Governance, Action Transactions,
Pre-Flight Validation, Commit/Rollback, and Verified Outcomes.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import pytest
from unittest.mock import AsyncMock

from app.decision.domain import (
    DecisionInput,
    DecisionLifecycleState,
    DecisionOption,
    DecisionType,
    DecisionV2Record,
)
from app.decision.intelligence_service import DecisionIntelligenceService
from app.execution.domain import (
    ALLOWED_TRANSACTION_TRANSITIONS,
    ActionObservation,
    ActionTransaction,
    OutcomeType,
    PostCondition,
    PreflightCheckResult,
    TargetBinding,
    TargetType,
    TransactionStatus,
    VerificationState,
)
from app.execution.preflight import PreflightValidationEngine
from app.execution.service import ExecutionGovernanceService
from app.execution.verification import ExecutionVerificationEngine
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError
from app.security.permissions import PermissionLevel
from app.security.policies import SecurityDecision
from app.tools.schemas import ToolCall, ToolResult


# ==============================================================================
# 1. State Machine & Domain Invariants (Phases 1 & 2)
# ==============================================================================

def test_all_22_transaction_states_defined():
    """Verify all 22 required states exist in TransactionStatus."""
    expected_states = {
        "CREATED", "PREPARING", "PREFLIGHT", "BLOCKED", "AWAITING_APPROVAL",
        "AUTHORIZED", "ALLOCATED", "READY", "EXECUTING", "PAUSED",
        "OBSERVING", "VERIFYING", "SUCCEEDED", "FAILED", "UNKNOWN",
        "ROLLING_BACK", "ROLLED_BACK", "RECOVERING", "RECOVERED",
        "CANCELLED", "EXPIRED", "SUPERSEDED",
    }
    actual_states = {s.value for s in TransactionStatus}
    assert expected_states == actual_states
    assert len(TransactionStatus) == 22


def test_transaction_state_transitions_enforced():
    """Verify legal transitions succeed and illegal jumps fail closed."""
    txn = ActionTransaction(
        transaction_id="txn_test_1",
        decision_id="dec_test_1",
        task_id="task_test_1",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        status=TransactionStatus.CREATED,
        idempotency_key="idem_1",
        target=TargetBinding(target_type=TargetType.SERVICE, target_id="srv_core"),
    )

    # Legal transition: CREATED -> PREPARING -> PREFLIGHT
    txn.transition_to(TransactionStatus.PREPARING)
    assert txn.status == TransactionStatus.PREPARING

    txn.transition_to(TransactionStatus.PREFLIGHT)
    assert txn.status == TransactionStatus.PREFLIGHT

    # Illegal jump: PREFLIGHT -> SUCCEEDED is not allowed without execution
    with pytest.raises(ValueError, match="Illegal transaction transition"):
        txn.transition_to(TransactionStatus.SUCCEEDED)

    # Illegal jump: PREFLIGHT -> EXECUTING without AUTHORIZED/ALLOCATED/READY
    with pytest.raises(ValueError, match="Illegal transaction transition"):
        txn.transition_to(TransactionStatus.EXECUTING)


def test_terminal_states_cannot_jump_to_executing():
    """Terminal states like SUCCEEDED, ROLLED_BACK, CANCELLED cannot transition to EXECUTING."""
    txn = ActionTransaction(
        transaction_id="txn_terminal",
        decision_id="dec_terminal",
        task_id="task_terminal",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        status=TransactionStatus.SUCCEEDED,
        idempotency_key="idem_term",
        target=TargetBinding(target_type=TargetType.SERVICE, target_id="srv_term"),
    )

    assert txn.can_transition_to(TransactionStatus.EXECUTING) is False
    with pytest.raises(ValueError, match="Illegal transaction transition"):
        txn.transition_to(TransactionStatus.EXECUTING)


# ==============================================================================
# 2. 18-Gate Pre-Flight Validation (Phase 3)
# ==============================================================================

@pytest.mark.asyncio
async def test_preflight_blocks_nonexistent_decision():
    """Gate 1: Pre-flight must block if originating decision does not exist."""
    dec_service = DecisionIntelligenceService()
    engine = PreflightValidationEngine(decision_service=dec_service)
    txn = ActionTransaction(
        transaction_id="txn_pf_1",
        decision_id="dec_nonexistent",
        task_id="task_1",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        status=TransactionStatus.PREFLIGHT,
        idempotency_key="key_1",
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="api_endpoint"),
    )

    passed, results = await engine.validate_transaction(txn, decision=None)
    assert passed is False
    assert any(r.gate_name == "gate_1_decision_currency" and not r.passed for r in results)


@pytest.mark.asyncio
async def test_preflight_blocks_expired_decision():
    """Gate 2: Pre-flight must block if decision TTL has expired."""
    dec_service = DecisionIntelligenceService()
    engine = PreflightValidationEngine(decision_service=dec_service)
    expired_dec = DecisionV2Record(
        id="dec_expired",
        decision_type=DecisionType.ACTION,
        title="Expired Action Decision",
        lifecycle_state=DecisionLifecycleState.SELECTED,
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    txn = ActionTransaction(
        transaction_id="txn_pf_2",
        decision_id="dec_expired",
        task_id="task_1",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        status=TransactionStatus.PREFLIGHT,
        idempotency_key="key_2",
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="api_endpoint"),
    )

    passed, results = await engine.validate_transaction(txn, decision=expired_dec)
    assert passed is False
    assert any(r.gate_name == "gate_2_decision_freshness" and not r.passed for r in results)


@pytest.mark.asyncio
async def test_preflight_blocks_retired_capability_version():
    """Gate 7: Pre-flight must block retired capability versions."""
    dec_service = DecisionIntelligenceService()
    engine = PreflightValidationEngine(decision_service=dec_service)
    active_dec = DecisionV2Record(
        id="dec_active",
        decision_type=DecisionType.ACTION,
        title="Active Decision",
        lifecycle_state=DecisionLifecycleState.SELECTED,
        objective_id="obj_123",
        expires_at=datetime.now(UTC) + timedelta(minutes=60),
    )
    txn = ActionTransaction(
        transaction_id="txn_pf_3",
        decision_id="dec_active",
        task_id="task_1",
        capability_id="calculator",
        capability_version="retired_v0.1",
        action_reference="tool:calculator",
        status=TransactionStatus.PREFLIGHT,
        idempotency_key="key_3",
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="api_endpoint"),
    )

    passed, results = await engine.validate_transaction(txn, decision=active_dec)
    assert passed is False
    assert any(r.gate_name == "gate_7_capability_version_usable" and not r.passed for r in results)


@pytest.mark.asyncio
async def test_preflight_blocks_when_emergency_stop_is_active():
    """Gate 13: EmergencyStop must fail closed in pre-flight validation."""
    EmergencyStopService.engage("Security drill active")
    dec_service = DecisionIntelligenceService()
    engine = PreflightValidationEngine(decision_service=dec_service)
    active_dec = DecisionV2Record(
        id="dec_active",
        decision_type=DecisionType.ACTION,
        title="Active Decision",
        lifecycle_state=DecisionLifecycleState.SELECTED,
        objective_id="obj_123",
        expires_at=datetime.now(UTC) + timedelta(minutes=60),
    )
    txn = ActionTransaction(
        transaction_id="txn_pf_4",
        decision_id="dec_active",
        task_id="task_1",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        status=TransactionStatus.PREFLIGHT,
        idempotency_key="key_4",
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="api_endpoint"),
    )

    try:
        passed, results = await engine.validate_transaction(txn, decision=active_dec)
        assert passed is False
        assert any(r.gate_name == "gate_13_emergency_stop_inactive" and not r.passed for r in results)
    finally:
        EmergencyStopService.disengage()


@pytest.mark.asyncio
async def test_preflight_blocks_oversized_parameters():
    """Gate 14: Oversized payloads (>64KB) must be rejected."""
    dec_service = DecisionIntelligenceService()
    engine = PreflightValidationEngine(decision_service=dec_service)
    active_dec = DecisionV2Record(
        id="dec_active",
        decision_type=DecisionType.ACTION,
        title="Active Decision",
        lifecycle_state=DecisionLifecycleState.SELECTED,
        objective_id="obj_123",
        expires_at=datetime.now(UTC) + timedelta(minutes=60),
    )
    oversized_params = {"blob": "x" * 70000}
    txn = ActionTransaction(
        transaction_id="txn_pf_5",
        decision_id="dec_active",
        task_id="task_1",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        parameters=oversized_params,
        status=TransactionStatus.PREFLIGHT,
        idempotency_key="key_5",
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="api_endpoint"),
    )

    passed, results = await engine.validate_transaction(txn, decision=active_dec)
    assert passed is False
    assert any(r.gate_name == "gate_14_parameter_schema_valid" and not r.passed for r in results)


# ==============================================================================
# 3. Idempotency & Target Binding (Phases 8 & 10)
# ==============================================================================

@pytest.mark.asyncio
async def test_idempotency_returns_existing_transaction():
    """Duplicate requests with the same parameters must return the existing transaction."""
    dec_service = DecisionIntelligenceService()
    service = ExecutionGovernanceService(decision_service=dec_service)
    dec = dec_service.deliberate(DecisionInput(
        title="Deploy Cluster Worker",
        description="Idempotent deployment test",
        decision_type=DecisionType.ACTION,
        candidate_options=[DecisionOption(id="opt_1", title="Deploy", alignment_score=0.9)],
    ))

    target = TargetBinding(target_type=TargetType.SERVICE, target_id="worker_pool_alpha")
    params = {"replicas": 3, "env": "prod"}

    txn1 = await service.prepare_transaction(
        decision_id=dec.id,
        capability_id="kairo_system",
        action_reference="tool:calculator",
        parameters=params,
        target=target,
    )

    txn2 = await service.prepare_transaction(
        decision_id=dec.id,
        capability_id="kairo_system",
        action_reference="tool:calculator",
        parameters=params,
        target=target,
    )

    assert txn1.transaction_id == txn2.transaction_id
    assert txn1.idempotency_key == txn2.idempotency_key


# ==============================================================================
# 4. Observation & Verification Engine (Phases 15, 16, 17, 18, 19)
# ==============================================================================

@pytest.mark.asyncio
async def test_verification_passed_all_postconditions():
    """Completed action with satisfied postconditions yields VERIFIED_SUCCESS."""
    engine = ExecutionVerificationEngine()
    txn = ActionTransaction(
        transaction_id="txn_ver_pass",
        decision_id="dec_pass",
        task_id="task_pass",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        status=TransactionStatus.VERIFYING,
        idempotency_key="key_ver_1",
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="endpoint_pass"),
        postconditions=[
            PostCondition(name="status_code_200", description="status_code check passed"),
            PostCondition(name="file_written", description="file exists on disk"),
        ],
    )

    tool_result = ToolResult(
        tool_name="calculator",
        success=True,
        output="Execution succeeded with status_code 200",
        exit_code=0,
    )

    ver_state, outcome, summary = await engine.verify_transaction(txn, tool_result)
    assert ver_state == VerificationState.PASSED
    assert outcome == OutcomeType.FULL_SUCCESS
    assert summary["satisfied_postconditions"] == 2


@pytest.mark.asyncio
async def test_verification_failed_when_tool_fails():
    """Tool failure immediately yields FAILED verification."""
    engine = ExecutionVerificationEngine()
    txn = ActionTransaction(
        transaction_id="txn_ver_fail",
        decision_id="dec_fail",
        task_id="task_fail",
        capability_id="calculator",
        capability_version="1.0.0",
        action_reference="tool:calculator",
        status=TransactionStatus.VERIFYING,
        idempotency_key="key_ver_2",
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="endpoint_fail"),
    )

    tool_result = ToolResult(
        tool_name="calculator",
        success=False,
        output="",
        error="Connection refused",
        exit_code=1,
    )

    ver_state, outcome, summary = await engine.verify_transaction(txn, tool_result)
    assert ver_state == VerificationState.FAILED
    assert outcome == OutcomeType.FAILED


# ==============================================================================
# 5. Rollback Compensation (Phase 20)
# ==============================================================================

@pytest.mark.asyncio
async def test_rollback_transaction_lifecycle():
    """Rollback must transition ROLLING_BACK -> ROLLED_BACK and dispatch compensation."""
    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(return_value=ToolResult(tool_name="calculator", success=True, output="Compensated"))

    dec_service = DecisionIntelligenceService()
    service = ExecutionGovernanceService(tool_executor=mock_executor, decision_service=dec_service)
    dec = dec_service.deliberate(DecisionInput(
        title="Rollback test decision",
        description="Testing compensation",
        decision_type=DecisionType.ACTION,
        candidate_options=[DecisionOption(id="opt_rb", title="Action", alignment_score=0.9)],
    ))

    txn = await service.prepare_transaction(
        decision_id=dec.id,
        capability_id="calculator",
        action_reference="tool:calculator",
        parameters={"expression": "1+1"},
        target=TargetBinding(target_type=TargetType.RESOURCE, target_id="res_test"),
        compensation_action="tool:calculator",
    )

    # Force transaction to FAILED state to initiate rollback
    txn.status = TransactionStatus.FAILED

    rb_txn = await service.rollback_transaction(txn.transaction_id, reason="Testing rollback")
    assert rb_txn.status == TransactionStatus.ROLLED_BACK
    assert rb_txn.rollback_reference is not None
    assert mock_executor.execute.called


# ==============================================================================
# 6. UNKNOWN State & Crash Reconciliation (Phases 22 & 37)
# ==============================================================================

@pytest.mark.asyncio
async def test_timeout_transitions_to_unknown_outcome():
    """When an execution times out, it must transition to UNKNOWN (not FAILED or SUCCESS)."""
    mock_executor = AsyncMock()
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(5.0)
        return ToolResult(tool_name="calculator", success=True, output="Done")
    mock_executor.execute = slow_execute

    dec_service = DecisionIntelligenceService()
    service = ExecutionGovernanceService(tool_executor=mock_executor, decision_service=dec_service)
    dec = dec_service.deliberate(DecisionInput(
        title="Timeout Decision",
        description="Testing timeout transition to UNKNOWN",
        decision_type=DecisionType.ACTION,
        candidate_options=[DecisionOption(id="opt_to", title="Slow Action", alignment_score=0.9)],
    ))

    txn = await service.prepare_transaction(
        decision_id=dec.id,
        capability_id="calculator",
        action_reference="tool:calculator",
        parameters={"expression": "1+1"},
        target=TargetBinding(target_type=TargetType.ENDPOINT, target_id="ep_slow"),
        timeout_seconds=0.1,  # Fast timeout
    )

    # Move to READY so execute can run
    txn.status = TransactionStatus.READY

    executed_txn = await service.execute_transaction(txn.transaction_id)
    assert executed_txn.status == TransactionStatus.UNKNOWN
    assert "timed out" in executed_txn.status_reason.lower()


@pytest.mark.asyncio
async def test_reconcile_unknown_transaction():
    """Reconciling an UNKNOWN transaction probes target state to confirm outcome."""
    dec_service = DecisionIntelligenceService()
    service = ExecutionGovernanceService(decision_service=dec_service)
    dec = dec_service.deliberate(DecisionInput(
        title="Reconcile Decision",
        description="Testing UNKNOWN reconciliation",
        decision_type=DecisionType.ACTION,
        candidate_options=[DecisionOption(id="opt_rc", title="Action", alignment_score=0.9)],
    ))

    txn = await service.prepare_transaction(
        decision_id=dec.id,
        capability_id="calculator",
        action_reference="tool:calculator",
        parameters={"expression": "1+1"},
        target=TargetBinding(target_type=TargetType.RESOURCE, target_id="res_probe"),
    )

    txn.status = TransactionStatus.UNKNOWN
    reconciled_txn = await service.reconcile_transaction(txn.transaction_id)

    # In synthetic evaluation, postconditions evaluate to true, so it recovers
    assert reconciled_txn.status in (TransactionStatus.RECOVERED, TransactionStatus.FAILED)


# ==============================================================================
# 7. Cancellation & Emergency Stop Priority (Phases 13 & 14)
# ==============================================================================

@pytest.mark.asyncio
async def test_cancellation_lifecycle():
    """Cancellation transitions transaction to CANCELLED and marks status_reason."""
    dec_service = DecisionIntelligenceService()
    service = ExecutionGovernanceService(decision_service=dec_service)
    dec = dec_service.deliberate(DecisionInput(
        title="Cancel Decision",
        description="Testing cancellation",
        decision_type=DecisionType.ACTION,
        candidate_options=[DecisionOption(id="opt_cn", title="Action", alignment_score=0.9)],
    ))

    txn = await service.prepare_transaction(
        decision_id=dec.id,
        capability_id="calculator",
        action_reference="tool:calculator",
        parameters={"expression": "1+1"},
        target=TargetBinding(target_type=TargetType.SERVICE, target_id="srv_cancel"),
    )

    cancelled_txn = await service.cancel_transaction(txn.transaction_id, reason="Manual operator stop")
    assert cancelled_txn.status == TransactionStatus.CANCELLED
    assert cancelled_txn.status_reason == "Manual operator stop"


@pytest.mark.asyncio
async def test_emergency_stop_blocks_execution_immediately():
    """EmergencyStop engagement blocks transaction preparation and execution immediately."""
    EmergencyStopService.engage("Emergency lockdown active")
    service = ExecutionGovernanceService()

    try:
        with pytest.raises(EmergencyStopActiveError):
            await service.prepare_transaction(
                decision_id="dec_any",
                capability_id="calculator",
                action_reference="tool:calculator",
                parameters={},
                target=TargetBinding(target_type=TargetType.MACHINE, target_id="m1"),
            )
    finally:
        EmergencyStopService.disengage()
