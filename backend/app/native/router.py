"""
FastAPI router for Kairo Native Runtime Substrate endpoints.
Prefix: /api/v1/native
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

try:
    from app.native.models import (
        CapabilityDescriptor,
        ExecutionRequest,
        ExecutionResult,
        ExecutionState,
        PreflightResult,
        ResponseStatus,
        RuntimeResponse,
    )
    from app.native.service import NativeRuntimeService
except ImportError:
    from backend.app.native.models import (
        CapabilityDescriptor,
        ExecutionRequest,
        ExecutionResult,
        ExecutionState,
        PreflightResult,
        ResponseStatus,
        RuntimeResponse,
    )
    from backend.app.native.service import NativeRuntimeService


router = APIRouter(prefix="/api/v1/native", tags=["Native Runtime"])


class ExecuteRequestSchema(BaseModel):
    operation: str = Field(..., description="Vetted native operation to execute")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Operation payload")
    deadline_ms: Optional[int] = Field(default=30000, description="Execution deadline in milliseconds")
    cancellation_id: Optional[str] = Field(default=None, description="Optional cancellation identifier")
    correlation_id: Optional[str] = Field(default=None, description="Distributed correlation ID")


class CancelRequestSchema(BaseModel):
    cancellation_id: str = Field(..., description="ID of the operation to cancel")


class PingRequestSchema(BaseModel):
    message: Optional[str] = Field(default="ping", description="Echo message")


def get_native_service() -> NativeRuntimeService:
    return NativeRuntimeService.get_instance()


@router.get("/health", summary="Get Native Runtime Health")
async def get_health(service: NativeRuntimeService = Depends(get_native_service)) -> Dict[str, Any]:
    return await service.get_health()


@router.get("/capabilities", summary="List Registered Native Capabilities", response_model=List[CapabilityDescriptor])
async def list_capabilities(service: NativeRuntimeService = Depends(get_native_service)) -> List[CapabilityDescriptor]:
    return await service.list_capabilities()


@router.post("/ping", summary="Ping Native Runtime", response_model=RuntimeResponse)
async def ping(
    req: PingRequestSchema = PingRequestSchema(),
    service: NativeRuntimeService = Depends(get_native_service),
) -> RuntimeResponse:
    return await service.execute(
        operation="sys.ping",
        payload={"message": req.message},
    )


@router.post("/execute", summary="Execute Vetted Native Operation", response_model=RuntimeResponse)
async def execute(
    req: ExecuteRequestSchema,
    service: NativeRuntimeService = Depends(get_native_service),
) -> RuntimeResponse:
    resp = await service.execute(
        operation=req.operation,
        payload=req.payload,
        deadline_ms=req.deadline_ms,
        cancellation_id=req.cancellation_id,
        correlation_id=req.correlation_id,
    )
    if resp.status == ResponseStatus.ERROR and resp.error:
        if resp.error.category.value == "AUTHORIZATION_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=resp.error.message,
            )
        elif resp.error.category.value == "INVALID_REQUEST":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=resp.error.message,
            )
    return resp


@router.post("/cancel", summary="Cancel In-Flight Native Operation")
async def cancel(
    req: CancelRequestSchema,
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    cancelled = await service.cancel(req.cancellation_id)
    return {
        "cancellation_id": req.cancellation_id,
        "cancelled": cancelled,
    }


# =============================================================================
# Sandbox Endpoints (Task 81)
# =============================================================================

@router.post("/sandbox/preflight", summary="Preflight Sandbox Evaluation", response_model=PreflightResult)
async def sandbox_preflight(
    req: ExecutionRequest,
    service: NativeRuntimeService = Depends(get_native_service),
) -> PreflightResult:
    """
    Perform dry-run preflight validation of an execution request.
    Computes effective sandbox policy, checks capability bounds,
    and returns whether execution would be admitted without running any code.
    """
    return await service.sandbox_preflight(req)


@router.post("/sandbox/execute", summary="Execute Sandboxed Workload", response_model=ExecutionResult)
async def sandbox_execute(
    req: ExecutionRequest,
    approval_id: Optional[str] = Query(default=None, description="Human approval ID if capability requires approval"),
    service: NativeRuntimeService = Depends(get_native_service),
) -> ExecutionResult:
    """
    Execute a typed native capability within the isolated Rust execution sandbox.
    Enforces EmergencyStop, SecurityCenter authorization, approval verification,
    and strict resource and stream boundaries.
    """
    result = await service.sandbox_execute(req, approval_id=approval_id)
    if result.state == ExecutionState.REJECTED and result.error:
        if result.error.category.value == "AUTHORIZATION_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result.error.message,
            )
        elif result.error.category.value == "INVALID_REQUEST":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error.message,
            )
    return result


@router.post("/sandbox/cancel", summary="Cancel Active Sandbox Execution")
async def sandbox_cancel(
    req: CancelRequestSchema,
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    """
    Cancel an active sandboxed workload by cancellation_id.
    Escalates termination to kill the process tree and cleans up isolated workspaces.
    """
    cancelled = await service.cancel(req.cancellation_id)
    return {
        "cancellation_id": req.cancellation_id,
        "cancelled": cancelled,
    }


@router.get("/economy/status", summary="Get Native Resource Economy Status")
async def get_economy_status(
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    """
    Retrieve aggregate native resource capacity, saturation, and active reservations.
    Connects Task 77 Resource Economy with Task 82 Native Enforcement Substrate.
    """
    return service.get_resource_economy_status()


@router.get("/economy/matrix", summary="Get Cross-Platform Resource Enforcement Matrix")
async def get_enforcement_matrix() -> List[Dict[str, Any]]:
    """
    Returns the honest cross-platform resource enforcement matrix.
    Clearly distinguishes HARD ENFORCED vs OBSERVABLE vs UNAVAILABLE.
    """
    return [
        {
            "resource": "MEMORY",
            "windows": "HARD_ENFORCED",
            "linux": "HARD_ENFORCED",
            "macos": "OBSERVABLE_ONLY",
            "mechanism": "Win32 Job Objects (JobMemoryLimit) / Linux cgroups (memory.max)",
        },
        {
            "resource": "WALL_CLOCK_TIME",
            "windows": "HARD_ENFORCED",
            "linux": "HARD_ENFORCED",
            "macos": "HARD_ENFORCED",
            "mechanism": "Tokio deadline racing with process tree kill",
        },
        {
            "resource": "CPU_TIME",
            "windows": "OBSERVED",
            "linux": "HARD_ENFORCED",
            "macos": "OBSERVED",
            "mechanism": "Win32 Job accounting (TotalUserTime+TotalKernelTime) / cgroups cpu.max",
        },
        {
            "resource": "PROCESS_COUNT",
            "windows": "HARD_ENFORCED",
            "linux": "HARD_ENFORCED",
            "macos": "OBSERVABLE_ONLY",
            "mechanism": "ActiveProcessLimit in Job Objects / Linux cgroups pids.max",
        },
        {
            "resource": "OUTPUT_BYTES",
            "windows": "HARD_ENFORCED",
            "linux": "HARD_ENFORCED",
            "macos": "HARD_ENFORCED",
            "mechanism": "Bounded stream readers with truncation and error tagging",
        },
        {
            "resource": "WORKSPACE_DISK",
            "windows": "HARD_ENFORCED",
            "linux": "HARD_ENFORCED",
            "macos": "HARD_ENFORCED",
            "mechanism": "Workspace growth monitoring with hard quota check",
        },
        {
            "resource": "FILE_COUNT",
            "windows": "HARD_ENFORCED",
            "linux": "HARD_ENFORCED",
            "macos": "HARD_ENFORCED",
            "mechanism": "Workspace recursive file enumeration limits",
        },
    ]


# =============================================================================
# Task 83: Native Tool Execution Fabric Endpoints
# =============================================================================

class ToolExecuteRequestSchema(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool input arguments")
    user_id: str = Field(default="default_user", description="Caller user ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    approval_id: Optional[str] = Field(default=None, description="Optional bound approval ID")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID")


@router.get("/tools", summary="List Registered Tools with Native Execution Metadata")
async def list_tools(
    service: NativeRuntimeService = Depends(get_native_service),
) -> List[Dict[str, Any]]:
    from app.tools.executor import get_tool_executor
    executor = get_tool_executor()
    health = await service.get_health()
    is_healthy = health.get("healthy", False)
    return executor.registry.get_native_tool_catalog(
        runtime_healthy=is_healthy,
        runtime_mode=service.mode,
    )


@router.get("/tools/health", summary="Get Tool Health and Execution Statistics")
async def get_tools_health() -> Dict[str, Any]:
    from app.tools.executor import get_tool_executor
    return get_tool_executor().registry.get_tool_metrics()


@router.get("/tools/{tool_name}", summary="Get Tool Details and Schema")
async def get_tool_detail(
    tool_name: str,
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    from app.tools.executor import get_tool_executor
    executor = get_tool_executor()
    tool = executor.registry.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    health = await service.get_health()
    status = executor.registry.get_tool_status(tool_name, health.get("healthy", False), service.mode)
    metrics = executor.registry.get_tool_metrics(tool_name)
    defn = tool.definition
    return {
        "name": defn.name,
        "description": defn.description,
        "version": defn.version,
        "permission_level": defn.permission_level.value,
        "execution_class": defn.execution_class.value,
        "preference": defn.preference.value,
        "capability_id": defn.capability_id,
        "sandbox_profile": defn.sandbox_profile,
        "availability": status.value,
        "timeout_seconds": defn.timeout_seconds,
        "idempotent": defn.idempotent,
        "fallback_tool": defn.fallback_tool,
        "parameters_schema": defn.parameters_schema,
        "output_schema": defn.output_schema,
        "metrics": metrics,
    }


@router.post("/tools/{tool_name}/execute", summary="Execute Tool via ToolExecutor Fabric")
async def execute_tool_endpoint(
    tool_name: str,
    req: ToolExecuteRequestSchema,
) -> Dict[str, Any]:
    from app.tools.executor import get_tool_executor
    executor = get_tool_executor()
    res = await executor.execute_tool(
        name=tool_name,
        arguments=req.arguments,
        user_id=req.user_id,
        session_id=req.session_id,
        approval_id=req.approval_id,
        correlation_id=req.correlation_id,
    )
    return res.model_dump()


# =============================================================================
# Task 84: Native Computer Interaction Substrate REST Endpoints
# =============================================================================

class ScreenCaptureRequestSchema(BaseModel):
    display_id: Optional[int] = Field(default=None, description="Optional target display index")
    max_width: Optional[int] = Field(default=1920, ge=100, le=3840, description="Bounded maximum width")
    max_height: Optional[int] = Field(default=1080, ge=100, le=2160, description="Bounded maximum height")


class ClipboardWriteRequestSchema(BaseModel):
    text: str = Field(..., max_length=100000, description="Text string to write to clipboard")


class MouseActionRequestSchema(BaseModel):
    action: str = Field(default="move", description="Mouse action ('move' or 'click')")
    x: int = Field(default=0, description="X coordinate")
    y: int = Field(default=0, description="Y coordinate")
    button: str = Field(default="left", description="Mouse button ('left', 'right', 'middle')")
    click_count: int = Field(default=1, ge=1, le=3, description="Click count")
    target_context: Optional[Dict[str, Any]] = Field(default=None, description="Expected target window/process binding")
    approval_id: Optional[str] = Field(default=None, description="Optional bound approval ID")


class KeyboardActionRequestSchema(BaseModel):
    action: str = Field(default="type", description="Keyboard action ('type', 'press', 'down', 'up')")
    text: Optional[str] = Field(default=None, max_length=1000, description="Text to type")
    key: Optional[str] = Field(default=None, description="Key name to press")
    target_context: Optional[Dict[str, Any]] = Field(default=None, description="Expected target window/process binding")
    approval_id: Optional[str] = Field(default=None, description="Optional bound approval ID")


@router.get("/computer/windows", summary="Enumerate Host Windows")
async def list_windows_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    service: NativeRuntimeService = Depends(get_native_service),
) -> List[Dict[str, Any]]:
    return await service.list_windows(limit=limit)


@router.get("/computer/processes", summary="Enumerate Host Processes")
async def list_processes_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    service: NativeRuntimeService = Depends(get_native_service),
) -> List[Dict[str, Any]]:
    return await service.list_processes(limit=limit)


@router.get("/computer/displays", summary="Enumerate Display Monitors")
async def list_displays_endpoint(
    service: NativeRuntimeService = Depends(get_native_service),
) -> List[Dict[str, Any]]:
    return await service.list_displays()


@router.post("/computer/capture", summary="Capture Bounded Screen Frame")
async def capture_screen_endpoint(
    req: ScreenCaptureRequestSchema = ScreenCaptureRequestSchema(),
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    return await service.capture_screen(
        display_id=req.display_id,
        max_width=req.max_width,
        max_height=req.max_height,
    )


@router.get("/computer/clipboard", summary="Read Host Clipboard")
async def read_clipboard_endpoint(
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    return await service.read_clipboard()


@router.post("/computer/clipboard", summary="Write Host Clipboard")
async def write_clipboard_endpoint(
    req: ClipboardWriteRequestSchema,
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    return await service.write_clipboard(text=req.text)


@router.post("/computer/mouse", summary="Execute Native Mouse Action")
async def execute_mouse_endpoint(
    req: MouseActionRequestSchema,
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    return await service.execute_mouse(
        action=req.action,
        x=req.x,
        y=req.y,
        button=req.button,
        click_count=req.click_count,
        target_context=req.target_context,
        approval_id=req.approval_id,
    )


@router.post("/computer/keyboard", summary="Execute Native Keyboard Action")
async def execute_keyboard_endpoint(
    req: KeyboardActionRequestSchema,
    service: NativeRuntimeService = Depends(get_native_service),
) -> Dict[str, Any]:
    return await service.execute_keyboard(
        action=req.action,
        text=req.text,
        key=req.key,
        target_context=req.target_context,
        approval_id=req.approval_id,
    )



