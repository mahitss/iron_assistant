"""REST API endpoints for Proactive Intelligence feeds and user preferences."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.proactive.schemas import (
    ProactiveFeedResponse,
    UserProactiveSettingsRead,
    UserProactiveSettingsUpdate,
)
from app.proactive.service import ProactiveService

logger = logging.getLogger("kairo.api.proactive")

router = APIRouter(prefix="/proactive", tags=["proactive"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header, defaulting to 'default_user'."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.get("/feed", response_model=ProactiveFeedResponse)
async def get_proactive_feed(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ProactiveFeedResponse:
    """Retrieve ranked, actionable proactive feed of events and alerts."""
    return await ProactiveService.get_feed(
        db_session=session,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/settings", response_model=UserProactiveSettingsRead)
async def get_proactive_settings(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> UserProactiveSettingsRead:
    """Retrieve proactive preferences, priority thresholds, and quiet hours."""
    settings = await ProactiveService.get_or_create_settings(session, user_id)
    return UserProactiveSettingsRead.model_validate(settings)


@router.patch("/settings", response_model=UserProactiveSettingsRead)
async def update_proactive_settings(
    payload: UserProactiveSettingsUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> UserProactiveSettingsRead:
    """Update proactive preferences, category toggles, or quiet hours."""
    updated = await ProactiveService.update_settings(session, user_id, payload)
    return UserProactiveSettingsRead.model_validate(updated)
