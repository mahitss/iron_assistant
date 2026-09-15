"""Unit and integration tests for Task 85: Kairo Native Network Execution & Connection Fabric."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.events.registry import get_event_registry
from app.native.models import (
    NetworkOperationClass,
    NetworkProtocol,
    NetworkExecutionPolicy,
    DnsResolveRequest,
    DnsResolveResult,
    HttpRequestDescriptor,
    HttpResponseResult,
    NetworkHealthReport,
    ExecutionRequest,
    ExecutionResult,
    ExecutionState,
)
from app.native.service import NativeRuntimeService
from app.security.center import SecurityCenter
from app.security.emergency_stop import EmergencyStopService
from app.security.policies import SecurityDecision, evaluate_tool_policy
from app.security.risk import RiskLevel
from app.security.schemas import SecurityDecisionResult
from app.tools.base import ToolExecutionClass, ToolExecutionPreference
from app.tools.builtin.network import (
    NativeDnsResolveTool,
    NativeHttpFetchTool,
    NativeHttpRequestTool,
)
from app.tools.executor import ToolExecutor
from app.tools.permissions import PermissionLevel, PermissionManager
from app.tools.registry import ToolRegistry, create_default_tool_registry
from app.tools.schemas import ToolCall, ToolResult


@pytest.fixture
def populated_registry() -> ToolRegistry:
    return create_default_tool_registry()


@pytest.fixture
def mock_security_center() -> SecurityCenter:
    sc = MagicMock(spec=SecurityCenter)
    sc.authorize = AsyncMock(return_value=SecurityDecisionResult(
        decision=SecurityDecision.ALLOWED,
        risk_level=RiskLevel.LOW,
        reason="Test allowed",
    ))
    return sc


@pytest.fixture
def executor(populated_registry: ToolRegistry, mock_security_center: SecurityCenter) -> ToolExecutor:
    return ToolExecutor(
        registry=populated_registry,
        permission_manager=PermissionManager(),
        security_center=mock_security_center,
    )


# =============================================================================
# 1. Tool Registry & Discovery Tests
# =============================================================================

def test_network_tools_registered(populated_registry: ToolRegistry):
    """Ensure all Task 85 native network tools are registered in default registry."""
    assert populated_registry.has_tool("native_dns_resolve")
    assert populated_registry.has_tool("native_http_fetch")
    assert populated_registry.has_tool("native_http_request")


def test_tool_capabilities_and_permissions(populated_registry: ToolRegistry):
    """Verify tool metadata, capability IDs, sandbox profiles, and permissions."""
    dns_tool = populated_registry.get("native_dns_resolve")
    assert dns_tool.capability_id == "native.net.resolve"
    assert dns_tool.permission_level == PermissionLevel.READ
    assert dns_tool.execution_class == ToolExecutionClass.NATIVE_RUST
    assert dns_tool.sandbox_profile == "NETWORK_EGRESS"
    assert dns_tool.idempotent

    fetch_tool = populated_registry.get("native_http_fetch")
    assert fetch_tool.capability_id == "native.net.fetch"
    assert fetch_tool.permission_level == PermissionLevel.READ
    assert fetch_tool.execution_class == ToolExecutionClass.NATIVE_RUST
    assert fetch_tool.sandbox_profile == "NETWORK_EGRESS"
    assert fetch_tool.idempotent

    req_tool = populated_registry.get("native_http_request")
    assert req_tool.capability_id == "native.net.request"
    assert req_tool.permission_level == PermissionLevel.EXTERNAL
    assert req_tool.execution_class == ToolExecutionClass.NATIVE_RUST
    assert req_tool.sandbox_profile == "NETWORK_EGRESS"
    assert not req_tool.idempotent


# =============================================================================
# 2. Central Security Policies Tests
# =============================================================================

def test_network_security_policies():
    """Verify centralized security decisions for native network tools."""
    dec_dns, risk_dns = evaluate_tool_policy("native_dns_resolve")
    assert dec_dns == SecurityDecision.ALLOWED

    dec_fetch, risk_fetch = evaluate_tool_policy("native_http_fetch")
    assert dec_fetch == SecurityDecision.ALLOWED

    dec_req, risk_req = evaluate_tool_policy("native_http_request")
    assert dec_req == SecurityDecision.APPROVAL_REQUIRED


# =============================================================================
# 3. Fallback Execution & SSRF Validation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_dns_resolve_fallback_ssrf_filtering():
    """Verify safe fallback DNS resolution blocks private/loopback addresses."""
    tool = NativeDnsResolveTool()
    # 127.0.0.1 loopback
    res = await tool.execute(hostname="localhost")
    assert res.get("addresses") == [] or "error" in res or "blocked" in str(res.get("error", "")).lower()


@pytest.mark.asyncio
async def test_http_fetch_fallback_ssrf_filtering():
    """Verify safe fallback fetch blocks loopback/private destinations."""
    tool = NativeHttpFetchTool()
    res = await tool.execute(url="http://127.0.0.1:8080/secret")
    assert res.get("status_code") in (400, 403, 502) or "blocked" in str(res.get("error", "")).lower()


@pytest.mark.asyncio
async def test_http_request_fallback_scheme_validation():
    """Verify non-HTTP schemes are rejected."""
    tool = NativeHttpRequestTool()
    res = await tool.execute(url="file:///etc/passwd")
    assert res.get("status_code") == 400
    assert "not supported" in res.get("error", "")


# =============================================================================
# 4. Python Service Layer Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_service_verify_sandbox_authorization():
    """Verify NativeRuntimeService authorizes all native.net.* capabilities."""
    service = NativeRuntimeService.get_instance()
    for cap in ("native.net.resolve", "native.net.fetch", "native.net.request", "native.net.health"):
        authorized = await service._verify_sandbox_authorization(cap, None)
        assert authorized, f"Capability {cap} should be authorized"


@pytest.mark.asyncio
async def test_service_emergency_stop_halts_network_execution():
    """EmergencyStop check: halts network execution instantly before socket contact."""
    service = NativeRuntimeService()
    service.emergency_stop.trigger_emergency_stop(reason="Test containment drill")

    req = ExecutionRequest(
        request_id="net_test_123",
        capability_id="native.net.fetch",
        arguments=[],
        payload={"url": "https://example.com"},
    )
    result = await service.sandbox_execute(req)
    assert result.state == ExecutionState.REJECTED
    assert "EMERGENCY_STOP_ACTIVE" in result.failure_classification

    # Reset emergency stop for subsequent tests
    service.emergency_stop.reset_emergency_stop()


@pytest.mark.asyncio
async def test_service_resolve_dns_mock_dispatch():
    """Verify service.resolve_dns constructs ExecutionRequest and returns output."""
    service = NativeRuntimeService()
    mock_res = ExecutionResult(
        request_id="net_dns_test",
        execution_id="exec_dns_123",
        capability_id="native.net.resolve",
        state=ExecutionState.COMPLETED,
        exit_code=0,
        stdout='{"hostname": "example.com", "addresses": ["93.184.216.34"], "ttl_seconds": 60, "cached": false}',
    )
    with patch.object(service, "sandbox_execute", new_callable=AsyncMock, return_value=mock_res):
        out = await service.resolve_dns(hostname="example.com")
        assert out["hostname"] == "example.com"
        assert "93.184.216.34" in out["addresses"]


@pytest.mark.asyncio
async def test_service_http_fetch_mock_dispatch():
    """Verify service.http_fetch constructs ExecutionRequest and returns output."""
    service = NativeRuntimeService()
    mock_res = ExecutionResult(
        request_id="net_fetch_test",
        execution_id="exec_fetch_123",
        capability_id="native.net.fetch",
        state=ExecutionState.COMPLETED,
        exit_code=0,
        stdout='{"status_code": 200, "headers": {"content-type": "text/html"}, "body": "Hello World", "bytes_received": 11, "truncated": false}',
    )
    with patch.object(service, "sandbox_execute", new_callable=AsyncMock, return_value=mock_res):
        out = await service.http_fetch(url="https://example.com")
        assert out["status_code"] == 200
        assert out["body"] == "Hello World"


@pytest.mark.asyncio
async def test_service_get_network_health_mock_dispatch():
    """Verify service.get_network_health returns structured health telemetry."""
    service = NativeRuntimeService()
    mock_res = ExecutionResult(
        request_id="net_hlth_test",
        execution_id="exec_hlth_123",
        capability_id="native.net.health",
        state=ExecutionState.COMPLETED,
        exit_code=0,
        stdout='{"state": "HEALTHY", "active_requests": 0, "active_connections": 1, "circuit_breaker_open": false, "ssrf_blocks_total": 3}',
    )
    with patch.object(service, "sandbox_execute", new_callable=AsyncMock, return_value=mock_res):
        health = await service.get_network_health()
        assert health["state"] == "HEALTHY"
        assert health["ssrf_blocks_total"] == 3


# =============================================================================
# 5. Event Registry Audit Events Verification
# =============================================================================

def test_network_audit_events_registered():
    """Ensure all 16 Task 85 network events are registered in EventRegistry."""
    registry = get_event_registry()
    required_events = [
        "network.request.accepted",
        "network.request.started",
        "network.dns.resolved",
        "network.connection.opened",
        "network.ssrf.blocked",
        "network.request.completed",
        "network.request.failed",
        "network.request.cancelled",
        "network.request.timed_out",
        "network.retry.attempted",
        "network.circuit_breaker.opened",
        "network.circuit_breaker.half_open",
        "network.circuit_breaker.closed",
        "network.rate_limit.exceeded",
        "network.body.truncated",
        "network.emergency_stop",
    ]
    for evt in required_events:
        assert registry.get(evt) is not None, f"Audit event {evt} not registered"


# =============================================================================
# 6. Pydantic Models Conformance Tests
# =============================================================================

def test_network_pydantic_models():
    """Verify Pydantic models serialize and deserialize correctly."""
    policy = NetworkExecutionPolicy(
        max_redirects=5,
        response_size_limit_bytes=1048576,
    )
    serialized = policy.model_dump()
    assert serialized["max_redirects"] == 5
    assert serialized["response_size_limit_bytes"] == 1048576

    desc = HttpRequestDescriptor(
        url="https://api.github.com/zen",
        method="GET",
        operation_class=NetworkOperationClass.FETCH,
        headers={"Accept": "application/json"},
    )
    assert desc.method == "GET"
    assert desc.operation_class == NetworkOperationClass.FETCH

    res = HttpResponseResult(
        status_code=200,
        headers={"content-type": "text/plain"},
        body="Responsive is better than fast.",
        bytes_received=31,
    )
    assert res.status_code == 200
    assert not res.truncated

    health = NetworkHealthReport(
        state="HEALTHY",
        active_requests=0,
        active_connections=2,
        circuit_breaker_open=False,
    )
    assert health.state == "HEALTHY"
