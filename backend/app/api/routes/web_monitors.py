"""REST API endpoints for managing and triggering web change monitors."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.proactive.schemas import (
    WebMonitorCheckResult,
    WebMonitorCreate,
    WebMonitorRead,
    WebMonitorUpdate,
)
from app.proactive.service import ProactiveService
from app.tools.web.safety import SSRFViolationError, UnsafeURLError

logger = logging.getLogger("kairo.api.web_monitors")

router = APIRouter(prefix="/web-monitors", tags=["web-monitors"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header, defaulting to 'default_user'."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.get("", response_model=list[WebMonitorRead])
async def list_web_monitors(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[WebMonitorRead]:
    """List all web change monitors configured by the authenticated user."""
    items = await ProactiveService.list_web_monitors(session, user_id)
    return [WebMonitorRead.model_validate(item) for item in items]


@router.post("", response_model=WebMonitorRead, status_code=status.HTTP_201_CREATED)
async def create_web_monitor(
    payload: WebMonitorCreate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> WebMonitorRead:
    """Create a new web change monitor with SSRF and safety validation."""
    try:
        monitor = await ProactiveService.create_web_monitor(session, user_id, payload)
        return WebMonitorRead.model_validate(monitor)
    except (SSRFViolationError, UnsafeURLError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or prohibited URL: {exc}",
        ) from exc


@router.patch("/{monitor_id}", response_model=WebMonitorRead)
async def update_web_monitor(
    monitor_id: str,
    payload: WebMonitorUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> WebMonitorRead:
    """Update settings or URL of an existing web monitor."""
    try:
        updated = await ProactiveService.update_web_monitor(session, user_id, monitor_id, payload)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Web monitor '{monitor_id}' not found.",
            )
        return WebMonitorRead.model_validate(updated)
    except (SSRFViolationError, UnsafeURLError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or prohibited URL: {exc}",
        ) from exc


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_web_monitor(
    monitor_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a web monitor."""
    deleted = await ProactiveService.delete_web_monitor(session, user_id, monitor_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Web monitor '{monitor_id}' not found.",
        )


@router.post("/{monitor_id}/check", response_model=WebMonitorCheckResult)
async def check_web_monitor(
    monitor_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> WebMonitorCheckResult:
    """Execute change detection on a web monitor."""
    monitor = await ProactiveService.get_web_monitor(session, user_id, monitor_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Web monitor '{monitor_id}' not found.",
        )
    return await ProactiveService.check_web_monitor(session, monitor)
