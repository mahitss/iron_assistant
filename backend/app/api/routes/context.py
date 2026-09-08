"""REST API endpoints for Personal Context Engine inspection and personalization settings."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.schemas import (
    ContextItem,
    ContextPacket,
    ContextSettings,
    ContextSettingsUpdate,
)
from app.context.service import ContextEngine
from app.db.session import get_db_session
from app.memory.service import MemoryService

logger = logging.getLogger("kairo.api.context")

router = APIRouter(prefix="/context", tags=["Context Engine"])

_default_context_engine: ContextEngine | None = None


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_context_engine() -> ContextEngine:
    """Provide singleton ContextEngine instance."""
    global _default_context_engine
    if _default_context_engine is None:
        _default_context_engine = ContextEngine()
    return _default_context_engine


def get_memory_service_dep(db: AsyncSession | None = Depends(get_db_session)) -> MemoryService | None:
    """Optional dependency injecting MemoryService if DB session is active."""
    if db is not None:
        return MemoryService(session=db)
    return None


@router.get(
    "/current",
    response_model=ContextPacket,
    summary="Get current active context",
    description="Retrieve the bounded, prioritized context bundle for the active user session.",
)
async def get_current_context(
    session_id: str | None = Query(default=None, description="Optional chat session identifier"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    memory_service: MemoryService | None = Depends(get_memory_service_dep),
    engine: ContextEngine = Depends(get_context_engine),
) -> ContextPacket:
    """Resolve current context packet."""
    return await engine.resolve_context(
        user_id=user_id,
        message="",
        session_id=session_id,
        db_session=db,
        memory_service=memory_service,
    )


@router.get(
    "/projects/{project_id}",
    response_model=ContextPacket,
    summary="Get project context",
    description="Retrieve context elements specifically linked to a project.",
)
async def get_project_context(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    engine: ContextEngine = Depends(get_context_engine),
) -> ContextPacket:
    """Fetch project-scoped context."""
    return await engine.get_project_context(
        user_id=user_id,
        project_id=project_id,
        db_session=db,
    )


@router.get(
    "/search",
    response_model=list[ContextItem],
    summary="Search context across projects and memory",
    description="Query both structured project resources and memories using hybrid retrieval.",
)
async def search_context(
    q: str = Query(..., min_length=1, description="Search query string"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    memory_service: MemoryService | None = Depends(get_memory_service_dep),
    engine: ContextEngine = Depends(get_context_engine),
) -> list[ContextItem]:
    """Execute hybrid contextual search."""
    return await engine.search_context(
        user_id=user_id,
        query=q,
        db_session=db,
        memory_service=memory_service,
    )


@router.get(
    "/settings",
    response_model=ContextSettings,
    summary="Get context personalization settings",
)
async def get_context_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    engine: ContextEngine = Depends(get_context_engine),
) -> ContextSettings:
    """Retrieve user context toggles."""
    return await engine.get_user_settings(user_id=user_id, db_session=db)


@router.patch(
    "/settings",
    response_model=ContextSettings,
    summary="Update context personalization settings",
)
async def update_context_settings(
    payload: ContextSettingsUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    engine: ContextEngine = Depends(get_context_engine),
) -> ContextSettings:
    """Update context personalization toggles."""
    return await engine.update_user_settings(
        user_id=user_id,
        updates=payload,
        db_session=db,
    )
