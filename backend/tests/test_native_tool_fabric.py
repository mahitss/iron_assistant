"""Unit and integration tests for Task 83: Kairo Native Tool Execution Fabric."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.security.center import SecurityCenter
from app.security.policies import SecurityDecision
from app.security.risk import RiskLevel
from app.security.schemas import SecurityDecisionResult
from app.tools.base import (
    ToolAvailability,
    ToolExecutionClass,
    ToolExecutionPreference,
)
from app.tools.builtin.native import (
    NativeHashTool,
    NativeProbeTool,
    NativeSystemInfoTool,
    NativeWorkspaceInspectTool,
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

def test_native_tools_registered(populated_registry: ToolRegistry):
    """Ensure all Task 83 native tools are registered in the default registry."""
    assert populated_registry.has_tool("native_hash")
    assert populated_registry.has_tool("native_system_info")
    assert populated_registry.has_tool("native_workspace_inspect")
    assert populated_registry.has_tool("native_probe")

    native_tools = populated_registry.list_native_tools()
    native_names = {t.name for t in native_tools}
    assert "native_hash" in native_names
    assert "native_system_info" in native_names
    assert "native_workspace_inspect" in native_names
    assert "native_probe" in native_names


def test_native_tool_definitions(populated_registry: ToolRegistry):
    """Ensure tool definitions correctly reflect native contracts and capabilities."""
    hash_tool = populated_registry.get("native_hash")
    assert hash_tool is not None
    defn = hash_tool.definition
    assert defn.execution_class == ToolExecutionClass.NATIVE_RUST
    assert defn.preference == ToolExecutionPreference.NATIVE_PREFERRED
    assert defn.capability_id == "sandbox.hash"
    assert defn.permission_level == PermissionLevel.READ

    inspect_tool = populated_registry.get("native_workspace_inspect")
    assert inspect_tool is not None
    defn_inspect = inspect_tool.definition
    assert defn_inspect.execution_class == ToolExecutionClass.NATIVE_RUST
    assert defn_inspect.preference == ToolExecutionPreference.NATIVE_REQUIRED
    assert defn_inspect.capability_id == "native.file.inspect"


def test_tool_status_and_catalog(populated_registry: ToolRegistry):
    """Ensure availability status calculation and catalog export are accurate."""
    # When runtime is healthy
    status = populated_registry.get_tool_status("native_hash", runtime_healthy=True)
    assert status == ToolAvailability.AVAILABLE

    # When runtime is offline: NATIVE_PREFERRED is DEGRADED (has fallback)
    status_degraded = populated_registry.get_tool_status("native_hash", runtime_healthy=False)
    assert status_degraded == ToolAvailability.DEGRADED

    # When runtime is offline: NATIVE_REQUIRED is UNAVAILABLE
    status_unavail = populated_registry.get_tool_status("native_workspace_inspect", runtime_healthy=False)
    assert status_unavail == ToolAvailability.UNAVAILABLE

    # When disabled
    status_disabled = populated_registry.get_tool_status(
        "native_workspace_inspect", runtime_healthy=False, runtime_mode="DISABLED"
    )
    assert status_disabled == ToolAvailability.DISABLED

    catalog = populated_registry.get_native_tool_catalog(runtime_healthy=True)
    assert len(catalog) >= 4
    hash_cat = next(item for item in catalog if item["name"] == "native_hash")
    assert hash_cat["execution_class"] == "NATIVE_RUST"
    assert hash_cat["capability_id"] == "sandbox.hash"
    assert hash_cat["availability"] == "AVAILABLE"


def test_tool_metrics_recording(populated_registry: ToolRegistry):
    """Ensure invocations, latency, and reliability metrics update accurately."""
    populated_registry.record_invocation("native_hash", duration_ms=12.5, success=True)
    populated_registry.record_invocation("native_hash", duration_ms=15.0, success=True)
    populated_registry.record_invocation("native_hash", duration_ms=30.0, success=False, is_timeout=True)

    metrics = populated_registry.get_tool_metrics("native_hash")
    assert metrics["invocations"] == 3
    assert metrics["failures"] == 1
    assert metrics["timeouts"] == 1
    assert round(metrics["success_rate"], 2) == 0.67
    assert metrics["avg_latency_ms"] > 0


# =============================================================================
# 2. Execution Routing & Fallback Tests
# =============================================================================

@pytest.mark.asyncio
async def test_native_preferred_python_fallback(executor: ToolExecutor):
    """Ensure NATIVE_PREFERRED tool executes via verified Python fallback when runtime offline."""
    with patch("app.native.service.get_native_runtime_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = True
        mock_svc.get_health = AsyncMock(return_value={"healthy": False, "status": "UNAVAILABLE"})
        mock_get_svc.return_value = mock_svc

        call = ToolCall(id="call_fallback_1", name="native_hash", arguments={"text": "hello kairo"})
        res = await executor.execute(call)

        assert res.success is True
        assert res.tool_name == "native_hash"
        assert res.execution_class == "PYTHON"
        assert isinstance(res.result, dict)
        assert len(res.result["sha256"]) == 64
        assert res.verification_status == "verified"
        assert res.provenance.get("fallback") is True


@pytest.mark.asyncio
async def test_native_required_fails_closed_when_offline(executor: ToolExecutor):
    """Ensure NATIVE_REQUIRED tool fails closed with clean error when runtime offline."""
    with patch("app.native.service.get_native_runtime_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = True
        mock_svc.get_health = AsyncMock(return_value={"healthy": False, "status": "UNAVAILABLE"})
        mock_get_svc.return_value = mock_svc

        call = ToolCall(id="call_req_1", name="native_workspace_inspect", arguments={"path": "main.py"})
        res = await executor.execute(call)

        assert res.success is False
        assert "requires native runtime substrate" in res.error
        assert res.verification_status == "failed"
        assert res.execution_class == "NATIVE_RUST"


@pytest.mark.asyncio
async def test_native_execution_success(executor: ToolExecutor):
    """Ensure valid native tool dispatches to sandbox_execute and returns structured provenance."""
    from app.native.models import (
        ExecutionResult as NativeExecResult,
        ExecutionState,
        ResourceUsageTelemetry,
    )

    with patch("app.native.service.get_native_runtime_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = True
        mock_svc.get_health = AsyncMock(return_value={"healthy": True, "status": "READY"})
        mock_svc.emergency_stop.is_stopped.return_value = False

        mock_exec_res = NativeExecResult(
            request_id="req_test_123",
            execution_id="exec_test_123",
            capability_id="sandbox.hash",
            state=ExecutionState.COMPLETED,
            exit_code=0,
            stdout='{"sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789", "bytes": 11}',
            stderr="",
            duration_ms=5,
            resource_telemetry=ResourceUsageTelemetry(
                duration_ms=5,
                peak_memory_bytes=1048576,
            ),
        )
        mock_svc.sandbox_execute = AsyncMock(return_value=mock_exec_res)
        mock_get_svc.return_value = mock_svc

        call = ToolCall(id="call_nat_1", name="native_hash", arguments={"text": "hello kairo"})
        res = await executor.execute(call)

        assert res.success is True
        assert res.execution_class == "NATIVE_RUST"
        assert res.capability_id == "sandbox.hash"
        assert res.result["sha256"] == "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        assert res.verification_status == "verified"
        assert res.resource_telemetry is not None
        assert res.provenance["tool_version"] == "1.0.0"


# =============================================================================
# 3. Governance, Security, & EmergencyStop Invariants
# =============================================================================

@pytest.mark.asyncio
async def test_emergency_stop_halts_native_tool(executor: ToolExecutor):
    """Ensure active EmergencyStop blocks native tool execution immediately."""
    with patch("app.native.service.get_native_runtime_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = True
        mock_svc.get_health = AsyncMock(return_value={"healthy": True, "status": "READY"})
        mock_svc.emergency_stop.is_stopped.return_value = True
        mock_get_svc.return_value = mock_svc

        call = ToolCall(id="call_estop_1", name="native_hash", arguments={"text": "test"})
        res = await executor.execute(call)

        assert res.success is False
        assert "EmergencyStop" in res.error
        assert res.verification_status == "denied"
        mock_svc.sandbox_execute.assert_not_called()


@pytest.mark.asyncio
async def test_security_center_denial_blocks_native_tool(populated_registry: ToolRegistry):
    """Ensure SecurityCenter denial blocks execution before native dispatch."""
    mock_sc = MagicMock(spec=SecurityCenter)
    mock_sc.authorize = AsyncMock(return_value=SecurityDecisionResult(
        decision=SecurityDecision.DENIED,
        risk_level=RiskLevel.HIGH,
        reason="Security policy forbids hash tool for this user",
    ))
    executor = ToolExecutor(
        registry=populated_registry,
        permission_manager=PermissionManager(),
        security_center=mock_sc,
    )

    call = ToolCall(id="call_denied_1", name="native_hash", arguments={"text": "test"})
    res = await executor.execute(call)

    assert res.success is False
    assert "Security policy forbids hash tool" in res.error or "denied by Security Center" in res.error
    assert res.verification_status == "denied"


@pytest.mark.asyncio
async def test_approval_requirement_for_mutating_native_probe(executor: ToolExecutor):
    """Ensure native probe tool (PermissionLevel.EXECUTE) halts pending user approval."""
    # When no approval_id is supplied
    call = ToolCall(id="call_probe_1", name="native_probe", arguments={"mode": "normal"})
    res = await executor.execute(call, approval_id=None)

    assert res.success is False
    assert res.approval_required is True
    assert res.verification_status == "denied"
