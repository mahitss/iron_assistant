"""REST API endpoints for Kairo Device Runtime and Local Companion integration."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.devices.schemas import (
    DeviceCommandRequest,
    DeviceCommandResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceResponse,
    DeviceUpdateRequest,
)
from app.devices.service import DeviceService
from app.security.exceptions import (
    CapabilityDisabledError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)

logger = logging.getLogger("kairo.api.devices")

router = APIRouter(prefix="/devices", tags=["Devices"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_device_service(db: AsyncSession | None = Depends(get_db_session)) -> DeviceService:
    """Inject DeviceService dependency."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is currently unavailable.",
        )
    return DeviceService(db)


@router.post(
    "/register",
    response_model=DeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a companion device",
)
async def register_device(
    payload: DeviceRegisterRequest,
    user_id: str = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> DeviceRegisterResponse:
    """Register a new companion runtime under the authenticated user's account."""
    try:
        return await service.register_device(user_id=user_id, payload=payload)
    except Exception as exc:
        logger.error("Failed to register device: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register companion device.",
        ) from exc


@router.get(
    "",
    response_model=list[DeviceResponse],
    summary="List registered devices",
)
async def list_devices(
    include_revoked: bool = Query(default=False, description="Include revoked devices in results"),
    user_id: str = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> list[DeviceResponse]:
    """Retrieve all devices owned by the authenticated user."""
    return await service.list_user_devices(user_id=user_id, include_revoked=include_revoked)


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Get device details",
)
async def get_device(
    device_id: str,
    user_id: str = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    """Retrieve metadata and capability states for a specific device."""
    try:
        return await service.get_device(user_id=user_id, device_id=device_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.patch(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Update device settings",
)
async def update_device(
    device_id: str,
    payload: DeviceUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    """Update device capabilities, name, or status."""
    try:
        return await service.update_device(user_id=user_id, device_id=device_id, payload=payload)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except SecurityPolicyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/{device_id}/revoke",
    response_model=DeviceResponse,
    summary="Revoke companion device",
)
async def revoke_device(
    device_id: str,
    user_id: str = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    """Revoke authorization for a device, instantly terminating its credentials."""
    try:
        return await service.revoke_device(user_id=user_id, device_id=device_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post(
    "/{device_id}/commands",
    response_model=DeviceCommandResponse,
    summary="Dispatch command to device",
)
async def dispatch_device_command(
    device_id: str,
    payload: DeviceCommandRequest,
    user_id: str = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> DeviceCommandResponse:
    """Dispatch a bounded, allowlisted action to an active companion device."""
    try:
        return await service.dispatch_command(user_id=user_id, device_id=device_id, payload=payload)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except CapabilityDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except SecurityPolicyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
