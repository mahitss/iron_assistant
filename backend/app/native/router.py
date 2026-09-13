"""
FastAPI router for Kairo Native Runtime Substrate endpoints.
Prefix: /api/v1/native
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

try:
    from app.native.models import CapabilityDescriptor, ResponseStatus, RuntimeResponse
    from app.native.service import NativeRuntimeService
except ImportError:
    from backend.app.native.models import CapabilityDescriptor, ResponseStatus, RuntimeResponse
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
