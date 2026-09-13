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

