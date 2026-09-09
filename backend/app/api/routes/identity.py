"""REST API routes for Kairo Identity, Sessions, Presence, and Cross-Interface Handoff (Spec 116)."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.identity.devices import IdentityDeviceManager
from app.identity.handoff import HandoffManager
from app.identity.presence import PresenceTracker
from app.identity.resolver import IdentityResolver
from app.identity.schemas import (
    ClientType,
    HandoffCompleteRequest,
    HandoffContextPacket,
    HandoffCreateRequest,
    HandoffResponse,
    IdentityErrorCode,
    PresenceResponse,
    PresenceUpdateRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionRevokeRequest,
    UserOnlineStatus,
)
from app.identity.sessions import SessionManager
from app.identity.trust import DeviceTrustManager
from app.security.exceptions import (
    CapabilityDisabledError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)

logger = logging.getLogger("kairo.api.identity")

router = APIRouter(prefix="/identity", tags=["Identity & Sessions"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_session_manager(db: AsyncSession | None = Depends(get_db_session)) -> SessionManager:
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.")
    return SessionManager(db)


def get_presence_tracker(db: AsyncSession | None = Depends(get_db_session)) -> PresenceTracker:
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.")
    return PresenceTracker(db)


def get_handoff_manager(db: AsyncSession | None = Depends(get_db_session)) -> HandoffManager:
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.")
    return HandoffManager(db)


def get_identity_resolver(db: AsyncSession | None = Depends(get_db_session)) -> IdentityResolver:
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.")
    return IdentityResolver(db)


# ==========================================
# Sessions API (Spec 116)
# ==========================================

@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="List active sessions",
)
async def list_sessions(
    include_revoked: bool = Query(default=False, description="Include revoked/expired sessions"),
    user_id: str = Depends(get_current_user_id),
    manager: SessionManager = Depends(get_session_manager),
) -> list[SessionResponse]:
    """Retrieve all active sessions belonging to the authenticated user."""
    return await manager.list_user_sessions(user_id=user_id, include_revoked=include_revoked)


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create interactive session",
)
async def create_session(
    payload: SessionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    manager: SessionManager = Depends(get_session_manager),
) -> SessionResponse:
    """Create a new interactive session bound to client type and optional device."""
    return await manager.create_session(
        user_id=user_id,
        client_type=payload.client_type,
        device_id=payload.device_id,
        metadata=payload.metadata,
    )


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=SessionResponse,
    summary="Revoke session",
)
async def revoke_session(
    session_id: str,
    payload: SessionRevokeRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    manager: SessionManager = Depends(get_session_manager),
) -> SessionResponse:
    """Explicitly revoke an active interactive session."""
    reason = payload.reason if payload else "User initiated revocation"
    try:
        return await manager.revoke_session(session_id=session_id, user_id=user_id, reason=reason)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post(
    "/sessions/revoke-all",
    summary="Sign out everywhere",
)
async def revoke_all_sessions(
    except_session_id: str | None = Query(default=None, description="Optional current session to keep active"),
    user_id: str = Depends(get_current_user_id),
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, Any]:
    """Global sign-out everywhere: revokes all active sessions for user (Spec 9, 78)."""
    count = await manager.revoke_all_sessions(user_id=user_id, except_session_id=except_session_id)
    return {
        "status": "success",
        "revoked_count": count,
        "message": f"Successfully revoked {count} active sessions.",
    }


# ==========================================
# Presence API (Spec 116)
# ==========================================

@router.get(
    "/presence",
    response_model=list[PresenceResponse],
    summary="Get interface presence",
)
async def get_presence(
    user_id: str = Depends(get_current_user_id),
    tracker: PresenceTracker = Depends(get_presence_tracker),
) -> list[PresenceResponse]:
    """Fetch current real-time application presence across user interfaces."""
    return await tracker.get_presence(user_id=user_id)


@router.post(
    "/presence/heartbeat",
    response_model=PresenceResponse,
    summary="Send presence heartbeat",
)
async def update_presence_heartbeat(
    payload: PresenceUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    tracker: PresenceTracker = Depends(get_presence_tracker),
) -> PresenceResponse:
    """Send rate-limited application heartbeat from an authorized interface (Spec 24, 119)."""
    try:
        return await tracker.update_presence(user_id=user_id, request=payload)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except SecurityPolicyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/presence/online-status",
    response_model=UserOnlineStatus,
    summary="Get user online state",
)
async def get_online_status(
    user_id: str = Depends(get_current_user_id),
    tracker: PresenceTracker = Depends(get_presence_tracker),
) -> UserOnlineStatus:
    """Return aggregated application online status without physical surveillance (Spec 23)."""
    return await tracker.get_user_online_status(user_id=user_id)


# ==========================================
# Handoff API (Spec 116)
# ==========================================

@router.post(
    "/handoff",
    response_model=HandoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate cross-interface handoff",
)
async def create_handoff(
    payload: HandoffCreateRequest,
    user_id: str = Depends(get_current_user_id),
    manager: HandoffManager = Depends(get_handoff_manager),
) -> HandoffResponse:
    """Create a single-use bounded context handoff token with explicit user consent (Spec 28-32)."""
    try:
        return await manager.create_handoff(user_id=user_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except SecurityPolicyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/handoff/{handoff_id}/complete",
    response_model=HandoffContextPacket,
    summary="Complete handoff",
)
async def complete_handoff(
    handoff_id: str,
    payload: HandoffCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    manager: HandoffManager = Depends(get_handoff_manager),
) -> HandoffContextPacket:
    """Consume single-use handoff ticket with anti-replay defenses (Spec 31, 32, 85)."""
    try:
        return await manager.complete_handoff(user_id=user_id, handoff_id=handoff_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except SecurityPolicyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==========================================
# Continuity & Ambiguity Resolution API
# ==========================================

@router.get(
    "/continuity/task",
    summary="Resolve task continuity",
)
async def resolve_task_continuity(
    task_id: str | None = Query(default=None, description="Optional target task ID"),
    project_id: str | None = Query(default=None, description="Optional project ID filter"),
    user_id: str = Depends(get_current_user_id),
    resolver: IdentityResolver = Depends(get_identity_resolver),
) -> dict[str, Any]:
    """Resolve active task continuity without guessing when ambiguous (Spec 41, 152)."""
    return await resolver.resolve_task_continuity(user_id=user_id, requested_task_id=task_id, project_id=project_id)


@router.get(
    "/continuity/device",
    summary="Resolve device target",
)
async def resolve_device_target(
    device_id: str | None = Query(default=None, description="Optional target device ID"),
    capability: str | None = Query(default=None, description="Required hardware capability"),
    user_id: str = Depends(get_current_user_id),
    resolver: IdentityResolver = Depends(get_identity_resolver),
) -> dict[str, Any]:
    """Resolve target device without guessing when multiple candidates exist (Spec 66, 153)."""
    try:
        return await resolver.resolve_device_target(user_id=user_id, explicit_device_id=device_id, required_capability=capability)
    except TenantIsolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
