"""Internal development and administration endpoints for explicit long-term memory management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.memory.sanitizer import UnsafeMemoryError
from app.memory.schemas import (
    MemoryCreate,
    MemoryResponse,
    MemorySearchResult,
    MemoryType,
    MemoryUpdate,
)
from app.memory.service import MemoryService

logger = logging.getLogger("kairo.api.memory")

router = APIRouter(prefix="/internal/memories", tags=["Internal Memory Management (Dev)"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_memory_service(db: AsyncSession | None = Depends(get_db_session)) -> MemoryService:
    """Dependency injecting MemoryService, ensuring database session is active."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured. Persistent memory service is currently inactive.",
        )
    return MemoryService(session=db)


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Internal] Explicitly store a long-term memory",
    description="Explicitly persist a sanitized long-term memory record with vector embeddings. Rejects sensitive data.",
)
async def create_memory(
    payload: MemoryCreate,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Store explicit persistent memory."""
    try:
        return await service.create_memory(
            content=payload.content,
            memory_type=payload.memory_type,
            importance=payload.importance,
            source=payload.source,
            user_id=user_id,
        )
    except UnsafeMemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Failed to create memory: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist memory entry.",
        )


@router.get(
    "/search",
    response_model=list[MemorySearchResult],
    summary="[Internal] Search long-term memories semantically",
    description="Query memories via vector similarity and composite ranking (similarity + importance + recency).",
)
async def search_memories(
    q: str = Query(..., min_length=1, description="Semantic search query string"),
    top_k: int = Query(default=5, ge=1, le=50, description="Max memories to return"),
    memory_type: MemoryType | None = Query(default=None, description="Optional memory type filter"),
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemorySearchResult]:
    """Perform semantic search over memories."""
    return await service.search_memories(
        query=q,
        top_k=top_k,
        memory_type=memory_type,
        user_id=user_id,
    )


@router.get(
    "",
    response_model=list[MemoryResponse],
    summary="[Internal] List recent memories",
    description="Retrieve stored long-term memories with optional type filtering.",
)
async def list_memories(
    memory_type: MemoryType | None = Query(default=None, description="Filter by memory type"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to retrieve"),
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryResponse]:
    """List recent persistent memories."""
    return await service.list_memories(memory_type=memory_type, limit=limit, user_id=user_id)


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="[Internal] Get memory by ID",
    description="Fetch a single long-term memory entry by its primary UUID.",
)
async def get_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Fetch memory entry by identifier."""
    mem = await service.get_memory(memory_id, user_id=user_id)
    if mem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found.",
        )
    return mem


@router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="[Internal] Update an existing memory",
    description="Update content, importance, or type of an existing memory.",
)
async def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Update fields of an existing memory."""
    try:
        updated = await service.update_memory(memory_id, payload, user_id=user_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory '{memory_id}' not found.",
            )
        return updated
    except UnsafeMemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Internal] Delete memory",
    description="Permanently delete a long-term memory record.",
)
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> None:
    """Remove a memory record."""
    deleted = await service.delete_memory(memory_id, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found.",
        )


# ==============================================================================
# User-facing Memory Inspection, Retrieval, Update and Deletion Endpoints (Section 14)
# ==============================================================================

memory_api_router = APIRouter(prefix="/memory", tags=["Memory Management"])
user_router = APIRouter(prefix="/memories", tags=["User Memory Management (Dev)"])


@memory_api_router.get(
    "",
    response_model=list[MemoryResponse],
    summary="List or search memories",
    description="Retrieve stored long-term memories with optional type, scope, and keyword filtering.",
)
@user_router.get(
    "",
    response_model=list[MemoryResponse],
    summary="List stored memories (User Control / Dev)",
    description="Retrieve stored long-term memories for inspection and management.",
)
async def list_user_memories(
    memory_type: MemoryType | None = Query(default=None, description="Filter by memory type"),
    limit: int = Query(default=50, ge=1, le=100, description="Max records to retrieve"),
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryResponse]:
    """List persistent memories for user review."""
    return await service.list_memories(memory_type=memory_type, limit=limit, user_id=user_id)


@memory_api_router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a memory by ID",
)
@user_router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a memory by ID",
)
async def get_user_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Fetch a specific memory by ID."""
    mem = await service.get_memory(memory_id, user_id=user_id)
    if mem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found.",
        )
    return mem


@memory_api_router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update an existing memory",
)
@user_router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update an existing memory",
)
async def update_user_memory(
    memory_id: str,
    payload: MemoryUpdate,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Update content or attributes of an existing memory."""
    try:
        updated = await service.update_memory(memory_id, payload, user_id=user_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory '{memory_id}' not found.",
            )
        return updated
    except UnsafeMemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@memory_api_router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a memory",
)
@user_router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a memory (User Control / Dev)",
    description="Permanently delete a stored memory record.",
)
async def delete_user_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> None:
    """Delete a specific memory by ID."""
    deleted = await service.delete_memory(memory_id, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found.",
        )
