"""
Unit tests for Kairo Native Secure Execution Sandbox:
- Protocol models (Pydantic v2 schemas, policies, intersection, serialization)
- NativeRuntimeService admission control, EmergencyStop invariants, SecurityCenter boundaries,
  and audit event emissions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.native.models import (
    EnvironmentMode,
    EnvironmentPolicy,
    ErrorCategory,
    ExecutionRequest,
    ExecutionResult,
    ExecutionState,
    FilesystemMode,
    FilesystemPolicy,
    NetworkMode,
    NetworkPolicy,
    OutputLimits,
    PreflightResult,
    ProcessTreePolicy,
    ResourceBudget,
    SandboxPolicy,
    SandboxProfile,
)
from app.native.service import NativeRuntimeService


# =============================================================================
# 1. Pydantic Models & Protocol Tests
# =============================================================================

def test_sandbox_policy_defaults():
    policy = SandboxPolicy()
    assert policy.profile == SandboxProfile.STANDARD
    assert policy.filesystem.mode == FilesystemMode.READ_ONLY
    assert policy.network.mode == NetworkMode.NO_NETWORK
    assert policy.environment.mode == EnvironmentMode.ALLOWLIST
    assert policy.process_tree.allow_child_processes is False
    assert policy.output_limits.max_stdout_bytes == 1024 * 1024


def test_execution_request_serialization_roundtrip():
    req = ExecutionRequest(
        capability_id="sandbox.echo",
        arguments=["hello", "world"],
        payload={"message": "hello world"},
        sandbox_policy=SandboxPolicy(
            profile=SandboxProfile.STRICT,
            network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
            output_limits=OutputLimits(max_stdout_bytes=65536),
        ),
    )
    raw = req.model_dump(mode="json")
    assert raw["capability_id"] == "sandbox.echo"
    assert raw["arguments"] == ["hello", "world"]
    assert raw["sandbox_policy"]["profile"] == "STRICT"

    restored = ExecutionRequest.model_validate(raw)
    assert restored.capability_id == req.capability_id
    assert restored.sandbox_policy.profile == SandboxProfile.STRICT
    assert restored.sandbox_policy.output_limits.max_stdout_bytes == 65536


def test_execution_result_states():
    result = ExecutionResult(
        request_id="req-123",
        execution_id="exec-456",
        capability_id="sandbox.echo",
        state=ExecutionState.COMPLETED,
        exit_code=0,
        stdout="echoed",
        duration_ms=42,
    )
    assert result.state == ExecutionState.COMPLETED
    assert result.exit_code == 0
    assert result.verification_metadata.process_exited is True
    assert result.verification_metadata.workspace_cleaned is True


# =============================================================================
# 2. Service Admission Control & Invariants Tests
# =============================================================================

@pytest.fixture
def mock_service():
    service = NativeRuntimeService.get_instance()
    # Save original state
    orig_mode = service.mode
    orig_client = service.client
    orig_estop = service.emergency_stop
    orig_sec = service.security_center
    orig_events = service.event_registry

    # Mock client
    mock_client = MagicMock()
    mock_client.sandbox_preflight = AsyncMock()
    mock_client.sandbox_execute = AsyncMock()
    mock_client.cancel = AsyncMock(return_value=True)

    # Mock event registry
    mock_events = MagicMock()
    mock_events.emit = AsyncMock()

    service.mode = "OPTIONAL"
    service.client = mock_client
    service.event_registry = mock_events

    yield service

    # Restore
    service.mode = orig_mode
    service.client = orig_client
    service.emergency_stop = orig_estop
    service.security_center = orig_sec
    service.event_registry = orig_events


@pytest.mark.asyncio
async def test_sandbox_execute_fails_closed_when_disabled(mock_service):
    mock_service.mode = "DISABLED"
    req = ExecutionRequest(capability_id="sandbox.echo")
    result = await mock_service.sandbox_execute(req)

    assert result.state == ExecutionState.REJECTED
    assert result.failure_classification == "NATIVE_RUNTIME_DISABLED"
    assert "disabled" in result.stderr.lower()
    mock_service.client.sandbox_execute.assert_not_called()


@pytest.mark.asyncio
async def test_sandbox_execute_fails_closed_when_emergency_stop_active(mock_service):
    # Activate emergency stop
    mock_service.emergency_stop.trigger_emergency_stop(reason="Test containment activation")
    try:
        req = ExecutionRequest(capability_id="sandbox.echo")
        result = await mock_service.sandbox_execute(req)

        assert result.state == ExecutionState.REJECTED
        assert result.failure_classification == "EMERGENCY_STOP_ACTIVE"
        assert result.error is not None
        assert result.error.category == ErrorCategory.AUTHORIZATION_REQUIRED
        mock_service.client.sandbox_execute.assert_not_called()
    finally:
        mock_service.emergency_stop.reset_emergency_stop(is_human_user=True)



@pytest.mark.asyncio
async def test_sandbox_execute_denied_by_security_center(mock_service):
    # Mock SecurityCenter returning False
    mock_service.security_center.is_allowed = MagicMock(return_value=False)

    req = ExecutionRequest(capability_id="privileged.sandbox.custom")
    result = await mock_service.sandbox_execute(req)

    assert result.state == ExecutionState.REJECTED
    assert result.failure_classification == "AUTHORIZATION_DENIED"
    assert result.error.category == ErrorCategory.AUTHORIZATION_REQUIRED
    mock_service.client.sandbox_execute.assert_not_called()


@pytest.mark.asyncio
async def test_sandbox_execute_requires_human_approval_for_destructive(mock_service):
    # Register a mock capability that is stateful/mutation
    mock_service.client.capabilities = AsyncMock(return_value=[])

    # If approval_id is None for a capability requiring approval, it must reject
    req = ExecutionRequest(
        capability_id="sandbox.execute",
        payload={"command": "mutation_op"},
    )
    result = await mock_service.sandbox_execute(req, approval_id=None)
    assert result.state == ExecutionState.REJECTED
    assert result.failure_classification == "APPROVAL_REQUIRED"


@pytest.mark.asyncio
async def test_sandbox_execute_dispatches_when_authorized(mock_service):
    expected_result = ExecutionResult(
        request_id="req-test-1",
        execution_id="exec-test-1",
        capability_id="sandbox.echo",
        state=ExecutionState.COMPLETED,
        exit_code=0,
        stdout="echo: hello world",
        duration_ms=15,
    )
    mock_service.client.sandbox_execute.return_value = expected_result

    req = ExecutionRequest(
        request_id="req-test-1",
        capability_id="sandbox.echo",
        arguments=["hello world"],
    )
    result = await mock_service.sandbox_execute(req)

    assert result.state == ExecutionState.COMPLETED
    assert result.stdout == "echo: hello world"
    mock_service.client.sandbox_execute.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_sandbox_preflight_dispatches_cleanly(mock_service):
    expected_preflight = PreflightResult(
        accepted=True,
        capability_id="sandbox.echo",
        effective_policy=SandboxPolicy(),
        effective_budget=ResourceBudget(),
    )
    mock_service.client.sandbox_preflight.return_value = expected_preflight

    req = ExecutionRequest(capability_id="sandbox.echo")
    result = await mock_service.sandbox_preflight(req)

    assert result.accepted is True
    assert result.capability_id == "sandbox.echo"
    mock_service.client.sandbox_preflight.assert_called_once_with(req)
