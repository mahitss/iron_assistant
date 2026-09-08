"""REST API endpoints for user in-app notification center."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.proactive.notifier import NotificationService
from app.proactive.schemas import NotificationActionResponse, NotificationRead

logger = logging.getLogger("kairo.api.notifications")

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header, defaulting to 'default_user'."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


class NotificationListResponse(BaseModel):
    """Notification listing response with unread count."""

    items: list[NotificationRead]
    total: int
    unread_count: int


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationListResponse:
    """List in-app notifications for the authenticated user."""
    items, total, unread = await NotificationService.list_notifications(
        db_session=session,
        user_id=user_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        items=[NotificationRead.model_validate(item) for item in items],
        total=total,
        unread_count=unread,
    )


@router.post("/{notification_id}/read", response_model=NotificationActionResponse)
async def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationActionResponse:
    """Mark notification as read."""
    updated = await NotificationService.mark_read(
        db_session=session,
        user_id=user_id,
        notification_id=notification_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification '{notification_id}' not found or access denied.",
        )
    return NotificationActionResponse(
        id=updated.id,
        status=updated.status,
        user_id=user_id,
    )


@router.post("/{notification_id}/dismiss", response_model=NotificationActionResponse)
async def mark_notification_dismissed(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationActionResponse:
    """Dismiss a notification from view."""
    updated = await NotificationService.mark_dismissed(
        db_session=session,
        user_id=user_id,
        notification_id=notification_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification '{notification_id}' not found or access denied.",
        )
    return NotificationActionResponse(
        id=updated.id,
        status=updated.status,
        user_id=user_id,
    )
