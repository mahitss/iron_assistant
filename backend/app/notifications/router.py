"""REST API endpoints for Kairo Unified Notification & Alerting Layer (Task 34, Spec 118, 119)."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.notifications.preferences import NotificationPreferencesManager
from app.notifications.schemas import (
    NotificationActionExecuteRequest,
    NotificationActionExecuteResponse,
    NotificationListResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationResponse,
)
from app.notifications.service import notification_service
from app.security.exceptions import ApprovalExpiredError, SecurityPolicyViolationError, TenantIsolationError

logger = logging.getLogger("kairo.notifications.router")

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header, defaulting to 'default_user'."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationPreferencesResponse:
    """Fetch user-scoped notification preferences."""
    record = await NotificationPreferencesManager.get_or_create_preferences(session, user_id)
    return NotificationPreferencesResponse.model_validate(record)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    request: NotificationPreferencesRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationPreferencesResponse:
    """Update user-scoped notification preferences."""
    record = await NotificationPreferencesManager.update_preferences(session, user_id, request)
    return NotificationPreferencesResponse.model_validate(record)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    priority_filter: str | None = Query(default=None, alias="priority"),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationListResponse:
    """List paginated notification history with filtering."""
    items, total, unread = await notification_service.list_notifications(
        db_session=session,
        user_id=user_id,
        status_filter=status_filter,
        type_filter=type_filter,
        priority_filter=priority_filter,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        items=[NotificationResponse.from_model(item) for item in items],
        total=total,
        unread_count=unread,
    )


@router.post("/read-all")
async def mark_all_read(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Mark all unread notifications as read for current user."""
    count = await notification_service.mark_all_read(session, user_id)
    return {"status": "success", "marked_read_count": count}


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationResponse:
    """Fetch details of a single notification."""
    try:
        notif = await notification_service.get_notification(session, user_id, notification_id)
        return NotificationResponse.from_model(notif)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification '{notification_id}' not found.")
    except TenantIsolationError as tie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(tie))


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationResponse:
    """Mark notification as read."""
    try:
        notif = await notification_service.mark_read(session, user_id, notification_id)
        return NotificationResponse.from_model(notif)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification '{notification_id}' not found.")
    except TenantIsolationError as tie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(tie))


@router.post("/{notification_id}/dismiss", response_model=NotificationResponse)
async def dismiss_notification(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationResponse:
    """Dismiss notification from view."""
    try:
        notif = await notification_service.dismiss(session, user_id, notification_id)
        return NotificationResponse.from_model(notif)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification '{notification_id}' not found.")
    except TenantIsolationError as tie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(tie))


@router.post("/{notification_id}/action", response_model=NotificationActionExecuteResponse)
async def execute_notification_action(
    notification_id: str,
    request: NotificationActionExecuteRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationActionExecuteResponse:
    """Safely execute an interactive action associated with a notification."""
    try:
        return await notification_service.execute_action(
            db_session=session,
            user_id=user_id,
            notification_id=notification_id,
            action_id=request.action_id,
            request=request,
        )
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except TenantIsolationError as tie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(tie))
    except ApprovalExpiredError as aee:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(aee))
    except SecurityPolicyViolationError as spe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(spe))
    except Exception as exc:
        logger.error("Failed executing notification action: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
