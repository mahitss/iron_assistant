"""Unit and integration tests for Task 84: Kairo Native Computer Interaction Substrate."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.events.registry import get_event_registry
from app.native.models import (
    ComputerOperationResult,
    DisplayMetadata,
    ExecutionRequest,
    ExecutionResult,
    ExecutionState,
    ProcessMetadata,
    TargetContext,
    VerificationStatus,
    WindowMetadata,
    WindowRect,
)
from app.native.service import NativeRuntimeService
from app.security.center import SecurityCenter
from app.security.policies import SecurityDecision, evaluate_tool_policy
from app.security.risk import RiskLevel
from app.security.schemas import SecurityDecisionResult
from app.tools.base import ToolExecutionClass, ToolExecutionPreference
from app.tools.builtin.computer import (
    NativeClipboardReadTool,
    NativeClipboardWriteTool,
    NativeDisplayInspectTool,
    NativeKeyboardActionTool,
    NativeMouseActionTool,
    NativeProcessInspectTool,
    NativeScreenCaptureTool,
    NativeWindowInspectTool,
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

def test_computer_tools_registered(populated_registry: ToolRegistry):
    """Ensure all Task 84 native computer tools are registered in default registry."""
    assert populated_registry.has_tool("native_window_inspect")
    assert populated_registry.has_tool("native_process_inspect")
    assert populated_registry.has_tool("native_display_inspect")
    assert populated_registry.has_tool("native_screen_capture")
    assert populated_registry.has_tool("native_clipboard_read")
    assert populated_registry.has_tool("native_clipboard_write")
    assert populated_registry.has_tool("native_mouse_action")
    assert populated_registry.has_tool("native_keyboard_action")


def test_tool_capabilities_and_permissions(populated_registry: ToolRegistry):
    """Verify tool metadata, capability IDs, and permissions."""
    win_tool = populated_registry.get("native_window_inspect")
    assert win_tool.capability_id == "native.window.inspect"
    assert win_tool.permission_level == PermissionLevel.READ
    assert win_tool.execution_class == ToolExecutionClass.NATIVE_RUST

    mouse_tool = populated_registry.get("native_mouse_action")
    assert mouse_tool.capability_id == "native.input.mouse"
    assert mouse_tool.permission_level == PermissionLevel.EXECUTE
    assert not mouse_tool.idempotent

    kbd_tool = populated_registry.get("native_keyboard_action")
    assert kbd_tool.capability_id == "native.input.keyboard"
    assert kbd_tool.permission_level == PermissionLevel.EXECUTE
    assert not kbd_tool.idempotent

    clip_w = populated_registry.get("native_clipboard_write")
    assert clip_w.capability_id == "native.clipboard.write"
    assert clip_w.permission_level == PermissionLevel.WRITE


# =============================================================================
# 2. Security Policy Overrides
# =============================================================================

def test_security_policy_evaluation():
    """Verify SecurityCenter evaluates computer tools with proper approval gating."""
    # Inspection tools are safe to inspect
    assert evaluate_tool_policy("native_window_inspect", {})[0] == SecurityDecision.ALLOWED
    assert evaluate_tool_policy("native_process_inspect", {})[0] == SecurityDecision.ALLOWED
    assert evaluate_tool_policy("native_display_inspect", {})[0] == SecurityDecision.ALLOWED
    assert evaluate_tool_policy("native_screen_capture", {})[0] == SecurityDecision.ALLOWED
    assert evaluate_tool_policy("native_clipboard_read", {})[0] == SecurityDecision.ALLOWED

    # Consequential mutating tools require approval
    assert evaluate_tool_policy("native_clipboard_write", {})[0] == SecurityDecision.APPROVAL_REQUIRED
    assert evaluate_tool_policy("native_mouse_action", {})[0] == SecurityDecision.APPROVAL_REQUIRED
    assert evaluate_tool_policy("native_keyboard_action", {})[0] == SecurityDecision.APPROVAL_REQUIRED


# =============================================================================
# 3. Python Fallback Verifications
# =============================================================================

@pytest.mark.asyncio
async def test_python_fallbacks():
    """Verify verified Python fallbacks execute correctly when native substrate is offline."""
    win_tool = NativeWindowInspectTool()
    res = await win_tool.execute(limit=10)
    assert win_tool.verify(res)
    assert len(res["windows"]) >= 1

    proc_tool = NativeProcessInspectTool()
    res = await proc_tool.execute(limit=10)
    assert proc_tool.verify(res)
    assert len(res["processes"]) >= 1

    disp_tool = NativeDisplayInspectTool()
    res = await disp_tool.execute()
    assert disp_tool.verify(res)
    assert len(res["displays"]) >= 1

    cap_tool = NativeScreenCaptureTool()
    res = await cap_tool.execute(max_width=1280, max_height=720)
    assert cap_tool.verify(res)
    assert res["status"] == "CAPTURED"
    assert res["bounded_width"] <= 1280

    mouse_tool = NativeMouseActionTool()
    res = await mouse_tool.execute(action="move", x=100, y=200, target_context={"expected_title": "test"})
    assert mouse_tool.verify(res)
    assert res["success"] is True
    assert res["target_verified"] is True

    kbd_tool = NativeKeyboardActionTool()
    res = await kbd_tool.execute(action="type", text="hello", target_context={"expected_title": "test"})
    assert kbd_tool.verify(res)
    assert res["success"] is True


# =============================================================================
# 4. EmergencyStop and Safety Boundaries
# =============================================================================

@pytest.mark.asyncio
async def test_emergency_stop_halts_native_computer_action():
    """Verify active EmergencyStop immediately rejects native computer operations."""
    service = NativeRuntimeService.get_instance()
    service.emergency_stop.trigger_emergency_stop(reason="Test E-Stop")

    try:
        req = ExecutionRequest(
            request_id="req-estop-1",
            capability_id="native.input.mouse",
            arguments=[],
            payload={"action": "click", "x": 100, "y": 100},
        )
        res = await service.sandbox_execute(req)
        assert res.state == ExecutionState.REJECTED
        assert "EmergencyStop" in res.stderr
        assert res.failure_classification == "EMERGENCY_STOP_ACTIVE"
    finally:
        service.emergency_stop.reset_emergency_stop(is_human_user=True)


# =============================================================================
# 5. Audit Events Registration
# =============================================================================

def test_computer_audit_events_registered():
    """Verify all 10 computer audit events exist in the central EventRegistry."""
    registry = get_event_registry()
    expected_events = [
        "computer.action.requested",
        "computer.action.authorized",
        "computer.action.rejected",
        "computer.action.started",
        "computer.action.completed",
        "computer.action.cancelled",
        "computer.action.failed",
        "computer.action.unverified",
        "computer.target.changed",
        "computer.emergency_stop",
    ]
    for ev in expected_events:
        reg = registry.get(ev)
        assert reg is not None, f"Event {ev} must be registered in EventRegistry"
        assert reg.security_class.value == "AUDIT_CRITICAL"


# =============================================================================
# 6. Target Context Model Validation
# =============================================================================

def test_target_context_model():
    """Verify TargetContext validation and binding."""
    ctx = TargetContext(
        window_id=12345,
        expected_title="Visual Studio Code",
        expected_pid=9876,
        expected_process_name="Code.exe",
        coordinate=(500, 300),
        display_id=0,
    )
    dumped = ctx.model_dump()
    assert dumped["expected_title"] == "Visual Studio Code"
    assert dumped["coordinate"] == (500, 300)

    # Empty target context is allowed for unconstrained moves
    empty_ctx = TargetContext()
    assert empty_ctx.expected_title is None
