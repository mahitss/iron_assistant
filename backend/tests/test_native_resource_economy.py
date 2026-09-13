"""
Unit and Integration tests for Task 82:
Kairo Native Resource Enforcement & Execution Economy.
Validates:
- Atomic reservation in ResourceRegistry before execution
- Guaranteed reservation release on all terminal states (no leaks)
- Backpressure when resource capacity is exhausted
- Variance calculation and estimation error learning
- Resource violation event emissions
- EmergencyStop supremacy overriding scheduling
"""

from __future__ import annotations

import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.native.models import (
    EnforcementAction,
    ErrorCategory,
    ExecutionRequest,
    ExecutionResult,
    ExecutionState,
    MeasurementQuality,
    ResourceBudget,
    ResourceUsageTelemetry,
    ResourceViolation,
    ResourceViolationType,
    SandboxPolicy,
    ViolationSeverity,
)
from app.native.service import NativeRuntimeService
from app.orchestration.resource_registry import ResourceRegistry
from app.orchestration.coordinator import ResourceEconomyCoordinator
from app.orchestration.economy import ResourceEconomyEngine
from app.orchestration.resources import create_resource
from app.orchestration.schemas import ResourceType, HealthStatus


@pytest.fixture
def economy_service():
    """Create an isolated NativeRuntimeService with fresh registry and mocked client."""
    registry = ResourceRegistry()
    economy_engine = ResourceEconomyEngine(resource_registry=registry)
    coordinator = ResourceEconomyCoordinator(economy_engine=economy_engine)

    mock_client = MagicMock()
    mock_client.sandbox_execute = AsyncMock()

    mock_events = MagicMock()
    mock_events.emit = AsyncMock()

    service = NativeRuntimeService(
        client=mock_client,
        event_registry=mock_events,
        resource_registry=registry,
        economy_coordinator=coordinator,
    )
    service.mode = "OPTIONAL"
    return service


@pytest.mark.asyncio
async def test_resource_reservation_and_clean_release(economy_service):
    """Verify resources are reserved before execution and released upon completion."""
    # Setup mock return value with telemetry
    telemetry = ResourceUsageTelemetry(
        wall_time_ms=120,
        cpu_time_ms=35,
        peak_memory_bytes=100 * 1024 * 1024, # 100 MiB actual
        current_memory_bytes=90 * 1024 * 1024,
        process_count=1,
        output_bytes=256,
        workspace_bytes=4096,
        file_count=2,
        measurement_quality=MeasurementQuality.EXACT,
    )
    expected_result = ExecutionResult(
        request_id="req_eco_1",
        execution_id="exec_eco_1",
        capability_id="sandbox.echo",
        state=ExecutionState.COMPLETED,
        exit_code=0,
        stdout="success",
        duration_ms=120,
        resource_telemetry=telemetry,
    )
    economy_service.client.sandbox_execute.return_value = expected_result

    req = ExecutionRequest(
        request_id="req_eco_1",
        capability_id="sandbox.echo",
        resource_budget=ResourceBudget(
            max_memory_bytes=512 * 1024 * 1024, # 512 MiB reserved
        ),
    )

    # Initial available capacity
    mem_res = economy_service.resource_registry.get("native_memory")
    initial_avail = mem_res.available_capacity

    result = await economy_service.sandbox_execute(req)
    assert result.state == ExecutionState.COMPLETED

    # Check that reservation was released (no leaks)
    assert mem_res.available_capacity == initial_avail
    assert mem_res.reserved_capacity == 0.0

    # Verify event emissions
    events = [call.args[0] for call in economy_service.event_registry.emit.call_args_list]
    assert "runtime.economy.reserved" in events
    assert "runtime.economy.released" in events
    assert "runtime.economy.reconciled" in events


@pytest.mark.asyncio
async def test_resource_backpressure_on_capacity_exhaustion(economy_service):
    """Verify that requests are rejected with backpressure when capacity is exhausted."""
    mem_res = economy_service.resource_registry.get("native_memory")
    # Drain capacity
    mem_res.available_capacity = 10.0 # only 10 MB left

    req = ExecutionRequest(
        request_id="req_eco_exhausted",
        capability_id="sandbox.echo",
        resource_budget=ResourceBudget(
            max_memory_bytes=512 * 1024 * 1024, # 512 MB requested
        ),
    )

    result = await economy_service.sandbox_execute(req)
    assert result.state == ExecutionState.REJECTED
    assert result.failure_classification == "RESOURCE_UNAVAILABLE"
    assert result.error is not None
    assert result.error.category == ErrorCategory.RESOURCE_LIMIT

    # Client was NOT called
    economy_service.client.sandbox_execute.assert_not_called()

    # Backpressure event was emitted
    events = [call.args[0] for call in economy_service.event_registry.emit.call_args_list]
    assert "runtime.economy.backpressure" in events


@pytest.mark.asyncio
async def test_reconciliation_variance_and_estimation_learning(economy_service):
    """Verify actual usage variance is calculated and fed to ResourceEconomyEngine for learning."""
    telemetry = ResourceUsageTelemetry(
        wall_time_ms=50,
        peak_memory_bytes=200 * 1024 * 1024, # 200 MiB actual
        measurement_quality=MeasurementQuality.EXACT,
    )
    expected_result = ExecutionResult(
        request_id="req_eco_learn",
        execution_id="exec_eco_learn",
        capability_id="sandbox.hash",
        state=ExecutionState.COMPLETED,
        exit_code=0,
        stdout="hashed",
        duration_ms=50,
        resource_telemetry=telemetry,
    )
    economy_service.client.sandbox_execute.return_value = expected_result

    req = ExecutionRequest(
        request_id="req_eco_learn",
        capability_id="sandbox.hash",
        resource_budget=ResourceBudget(
            max_memory_bytes=512 * 1024 * 1024, # 512 MiB reserved
        ),
    )

    await economy_service.sandbox_execute(req)

    # Check learning record
    historical = economy_service.economy_coordinator.economy._historical_demands
    assert "native:sandbox.hash" in historical
    assert len(historical["native:sandbox.hash"]) == 1
    assert abs(historical["native:sandbox.hash"][0] - 200.0) < 0.1

    # Check reconciliation payload in audit event
    reconciled_call = next(
        c for c in economy_service.event_registry.emit.call_args_list
        if c.args[0] == "runtime.economy.reconciled"
    )
    payload = reconciled_call.args[1]
    assert payload["reserved_memory_mb"] == 512.0
    assert payload["actual_memory_mb"] == 200.0
    assert payload["variance_mb"] == 312.0


@pytest.mark.asyncio
async def test_resource_violation_audit_emission(economy_service):
    """Verify that detected resource violations emit runtime.economy.violation event."""
    violation = ResourceViolation(
        violation_type=ResourceViolationType.MEMORY_LIMIT_EXCEEDED,
        severity=ViolationSeverity.HARD_LIMIT,
        limit_value=67108864,
        actual_value=134217728,
        unit="bytes",
        message="Peak memory exceeded effective 64 MB limit",
        enforcement_action=EnforcementAction.TERMINATE,
    )
    expected_result = ExecutionResult(
        request_id="req_eco_violation",
        execution_id="exec_eco_violation",
        capability_id="sandbox.probe",
        state=ExecutionState.RESOURCE_EXCEEDED,
        exit_code=1,
        stderr="Peak memory exceeded effective 64 MB limit",
        duration_ms=80,
        resource_violation=violation,
    )
    economy_service.client.sandbox_execute.return_value = expected_result

    req = ExecutionRequest(
        request_id="req_eco_violation",
        capability_id="sandbox.probe",
    )

    result = await economy_service.sandbox_execute(req)
    assert result.state == ExecutionState.RESOURCE_EXCEEDED
    assert result.resource_violation is not None
    assert result.resource_violation.violation_type == ResourceViolationType.MEMORY_LIMIT_EXCEEDED

    # Check violation event
    events = [call.args[0] for call in economy_service.event_registry.emit.call_args_list]
    assert "runtime.economy.violation" in events


@pytest.mark.asyncio
async def test_emergency_stop_overrides_scheduling_and_releases(economy_service):
    """Verify that EmergencyStop immediately halts scheduling, rejects work, and leaves zero leaks."""
    economy_service.emergency_stop.trigger_emergency_stop(reason="Security incident containment")

    try:
        req = ExecutionRequest(
            request_id="req_eco_estop",
            capability_id="sandbox.echo",
            resource_budget=ResourceBudget(max_memory_bytes=256 * 1024 * 1024),
        )

        mem_res = economy_service.resource_registry.get("native_memory")
        initial_avail = mem_res.available_capacity

        result = await economy_service.sandbox_execute(req)

        assert result.state == ExecutionState.REJECTED
        assert result.failure_classification == "EMERGENCY_STOP_ACTIVE"
        assert result.error is not None
        assert result.error.category == ErrorCategory.AUTHORIZATION_REQUIRED

        # Zero reservation leaks
        assert mem_res.available_capacity == initial_avail
        assert mem_res.reserved_capacity == 0.0

        # Client was never invoked
        economy_service.client.sandbox_execute.assert_not_called()
    finally:
        economy_service.emergency_stop.reset_emergency_stop(is_human_user=True)

