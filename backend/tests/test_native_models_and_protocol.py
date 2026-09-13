"""
Unit tests for Kairo Native Runtime Protocol Models and Schemas (Task 80).
Verifies Pydantic v2 schemas, bounds validation, and serialization roundtrips.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

try:
    from app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        ExecutionClass,
        HandshakeRequest,
        HandshakeResponse,
        HealthState,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        SideEffectClass,
        TimingMetadata,
    )
except ImportError:
    from backend.app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        ExecutionClass,
        HandshakeRequest,
        HandshakeResponse,
        HealthState,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        SideEffectClass,
        TimingMetadata,
    )


def test_protocol_version_constant():
    assert CURRENT_PROTOCOL_VERSION == "1.0"


def test_resource_budget_validation_valid():
    budget = ResourceBudget(
        max_cpu_percent=50.0,
        max_memory_bytes=1024 * 1024 * 100,
        max_execution_time_ms=10000,
        max_concurrency=4,
        max_output_bytes=1024 * 512,
    )
    assert budget.max_cpu_percent == 50.0
    assert budget.max_memory_bytes == 104857600
    assert budget.max_execution_time_ms == 10000


def test_resource_budget_bounds_rejection():
    # Negative CPU percent
    with pytest.raises(ValidationError):
        ResourceBudget(max_cpu_percent=-10.0)

    # CPU > 100
    with pytest.raises(ValidationError):
        ResourceBudget(max_cpu_percent=120.0)

    # Duration > 300,000 ms (5 minutes ceiling)
    with pytest.raises(ValidationError):
        ResourceBudget(max_execution_time_ms=400000)

    # Zero duration
    with pytest.raises(ValidationError):
        ResourceBudget(max_execution_time_ms=0)

    # Concurrency > 64
    with pytest.raises(ValidationError):
        ResourceBudget(max_concurrency=100)


def test_runtime_request_roundtrip():
    req = RuntimeRequest(
        operation="sys.ping",
        deadline_ms=15000,
        cancellation_id="cancel-test-1",
        correlation_id="corr-trace-99",
        caller_context=RequestContext(
            user_id="usr-test",
            tenant_id="ten-main",
            security_level="ADMIN",
        ),
        resource_budget=ResourceBudget(max_execution_time_ms=5000),
        payload={"ping": "pong"},
    )

    json_str = req.model_dump_json()
    reloaded = RuntimeRequest.model_validate_json(json_str)

    assert reloaded.request_id == req.request_id
    assert reloaded.protocol_version == "1.0"
    assert reloaded.operation == "sys.ping"
    assert reloaded.cancellation_id == "cancel-test-1"
    assert reloaded.caller_context is not None
    assert reloaded.caller_context.user_id == "usr-test"
    assert reloaded.payload == {"ping": "pong"}


def test_runtime_response_success():
    resp = RuntimeResponse(
        request_id="req-123",
        protocol_version="1.0",
        status=ResponseStatus.OK,
        result={"echo": "success"},
        timing=TimingMetadata(queue_time_ms=1, execution_time_ms=5, total_time_ms=6),
    )

    json_str = resp.model_dump_json()
    reloaded = RuntimeResponse.model_validate_json(json_str)

    assert reloaded.status == ResponseStatus.OK
    assert reloaded.result == {"echo": "success"}
    assert reloaded.error is None
    assert reloaded.timing is not None
    assert reloaded.timing.total_time_ms == 6


def test_runtime_response_error():
    resp = RuntimeResponse(
        request_id="req-456",
        protocol_version="1.0",
        status=ResponseStatus.ERROR,
        error=RuntimeErrorModel(
            category=ErrorCategory.AUTHORIZATION_REQUIRED,
            code="ACCESS_DENIED",
            message="Caller lacks native permission",
            retryable=False,
        ),
    )

    assert resp.status == ResponseStatus.ERROR
    assert resp.error is not None
    assert resp.error.category == ErrorCategory.AUTHORIZATION_REQUIRED
    assert not resp.error.retryable


def test_capability_descriptor_validation():
    cap = CapabilityDescriptor(
        capability_id="sys.ping",
        name="System Ping Probe",
        version="1.0.0",
        description="Low-latency health ping",
        available=True,
        execution_class=ExecutionClass.PURE_COMPUTE,
        side_effect_class=SideEffectClass.NONE,
        supported_operations=["sys.ping"],
    )

    assert cap.capability_id == "sys.ping"
    assert cap.execution_class == ExecutionClass.PURE_COMPUTE
    assert cap.side_effect_class == SideEffectClass.NONE


def test_handshake_schemas():
    req = HandshakeRequest(secret="super-secret", client_id="test-client")
    assert req.protocol_version == "1.0"
    assert req.secret == "super-secret"

    resp = HandshakeResponse(
        protocol_version="1.0",
        runtime_version="0.1.0",
        authenticated=True,
        capabilities=[],
    )
    assert resp.authenticated
    assert resp.error is None
