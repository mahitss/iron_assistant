"""REST API endpoints for Security Center: capabilities, approvals, audit, and emergency stop."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.security.approvals import ApprovalManager
from app.security.audit import AuditLogger
from app.security.center import SecurityCenter, get_security_center
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.security.exceptions import (
    ApprovalExpiredError,
    ApprovalInvalidError,
    SecurityError,
    TenantIsolationError,
)
from app.security.schemas import (
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    AuditEventResponse,
    AuditQueryResponse,
    CapabilitySettingsUpdate,
    EmergencyStopActionRequest,
    EmergencyStopResponse,
    UserCapabilitiesResponse,
)

logger = logging.getLogger("kairo.api.security")

router = APIRouter(prefix="/security", tags=["security"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract and validate the authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


# --- User Capabilities ---


@router.get("/settings", response_model=UserCapabilitiesResponse)
async def get_security_settings(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
    security_center: SecurityCenter = Depends(get_security_center),
) -> UserCapabilitiesResponse:
    """Retrieve capability gates and feature toggles for the authenticated user."""
    caps = await security_center.get_user_capabilities(session, user_id)
    return UserCapabilitiesResponse.model_validate(caps)


@router.patch("/settings", response_model=UserCapabilitiesResponse)
async def update_security_settings(
    payload: CapabilitySettingsUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
    security_center: SecurityCenter = Depends(get_security_center),
) -> UserCapabilitiesResponse:
    """Update capability gates for the authenticated user."""
    caps = await security_center.update_user_capabilities(session, user_id, payload)
    return UserCapabilitiesResponse.model_validate(caps)


# --- Approvals ---


@router.get("/approvals", response_model=list[ApprovalRequestResponse])
async def list_pending_approvals(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[ApprovalRequestResponse]:
    """List pending approval requests for the authenticated user."""
    approvals = await ApprovalManager.list_pending_approvals(session, user_id)
    return [ApprovalRequestResponse.model_validate(a) for a in approvals]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_action(
    approval_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalRequestResponse:
    """Approve a pending restricted action request."""
    try:
        req = await ApprovalManager.apply_decision(
            db_session=session,
            approval_id=approval_id,
            user_id=user_id,
            decision="approve",
        )
        await AuditLogger.log_event(
            db_session=session,
            user_id=user_id,
            event_type="security.approved",
            tool_name=req.tool_name,
            approval_id=req.id,
            decision="APPROVED",
            success=True,
            metadata={"arguments": req.arguments_summary},
        )
        return ApprovalRequestResponse.model_validate(req)
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (ApprovalInvalidError, ApprovalExpiredError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalRequestResponse)
async def deny_action(
    approval_id: str,
    payload: ApprovalDecisionRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalRequestResponse:
    """Deny a pending restricted action request."""
    reason = payload.reason if payload else None
    try:
        req = await ApprovalManager.apply_decision(
            db_session=session,
            approval_id=approval_id,
            user_id=user_id,
            decision="deny",
            reason=reason,
        )
        await AuditLogger.log_event(
            db_session=session,
            user_id=user_id,
            event_type="security.denied",
            tool_name=req.tool_name,
            approval_id=req.id,
            decision="DENIED",
            success=False,
            metadata={"reason": reason, "arguments": req.arguments_summary},
        )
        return ApprovalRequestResponse.model_validate(req)
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (ApprovalInvalidError, ApprovalExpiredError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# --- Audit Log ---


@router.get("/audit", response_model=AuditQueryResponse)
async def get_audit_trail(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
    tool_name: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> AuditQueryResponse:
    """Retrieve immutable audit events scoped strictly to the authenticated user."""
    items, total = await AuditLogger.query_events(
        db_session=session,
        user_id=user_id,
        limit=limit,
        offset=offset,
        event_type=event_type,
        tool_name=tool_name,
    )
    return AuditQueryResponse(
        items=[AuditEventResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# --- Emergency Stop ---


@router.get("/emergency-stop", response_model=EmergencyStopResponse)
async def get_emergency_stop_status(
    user_id: str = Depends(get_current_user_id),
    emergency_stop: EmergencyStopService = Depends(get_emergency_stop_service),
) -> EmergencyStopResponse:
    """Check whether emergency stop is currently active."""
    is_stop = emergency_stop.is_stopped(user_id)
    return EmergencyStopResponse(
        is_stopped=is_stop,
        status="STOPPED" if is_stop else "ACTIVE",
    )


@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def trigger_emergency_stop(
    payload: EmergencyStopActionRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
    emergency_stop: EmergencyStopService = Depends(get_emergency_stop_service),
) -> EmergencyStopResponse:
    """Activate the emergency kill switch for the user."""
    reason = payload.reason if payload else "User initiated stop"
    info = emergency_stop.trigger_emergency_stop(user_id=user_id, reason=reason)
    await AuditLogger.log_event(
        db_session=session,
        user_id=user_id,
        event_type="emergency_stop.enabled",
        decision="STOPPED",
        metadata={"reason": reason},
    )
    return EmergencyStopResponse(
        is_stopped=True,
        status="STOPPED",
        timestamp=info.get("timestamp"),
        reason=reason,
    )


@router.post("/emergency-stop/reset", response_model=EmergencyStopResponse)
async def reset_emergency_stop(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
    emergency_stop: EmergencyStopService = Depends(get_emergency_stop_service),
) -> EmergencyStopResponse:
    """Reset the emergency kill switch. Requires explicit user action; model cannot call."""
    try:
        emergency_stop.reset_emergency_stop(user_id=user_id, is_human_user=True)
        await AuditLogger.log_event(
            db_session=session,
            user_id=user_id,
            event_type="emergency_stop.disabled",
            decision="ACTIVE",
            metadata={"reset_by": "user"},
        )
        return EmergencyStopResponse(
            is_stopped=False,
            status="ACTIVE",
        )
    except SecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
