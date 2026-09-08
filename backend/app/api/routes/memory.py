"""Internal development and administration endpoints for explicit long-term memory management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Store explicit persistent memory."""
    try:
        return await service.create_memory(
            content=payload.content,
            memory_type=payload.memory_type,
            importance=payload.importance,
            source=payload.source,
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
    service: MemoryService = Depends(get_memory_service),
) -> list[MemorySearchResult]:
    """Perform semantic search over memories."""
    return await service.search_memories(
        query=q,
        top_k=top_k,
        memory_type=memory_type,
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
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryResponse]:
    """List recent persistent memories."""
    return await service.list_memories(memory_type=memory_type, limit=limit)


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="[Internal] Get memory by ID",
    description="Fetch a single long-term memory entry by its primary UUID.",
)
async def get_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Fetch memory entry by identifier."""
    mem = await service.get_memory(memory_id)
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
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Update fields of an existing memory."""
    try:
        updated = await service.update_memory(memory_id, payload)
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
    service: MemoryService = Depends(get_memory_service),
) -> None:
    """Remove a memory record."""
    deleted = await service.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found.",
        )


# ==============================================================================
# User-facing Memory Inspection and Deletion Endpoints (Section 14)
# ==============================================================================

user_router = APIRouter(prefix="/memories", tags=["User Memory Management (Dev)"])


@user_router.get(
    "",
    response_model=list[MemoryResponse],
    summary="List stored memories (User Control / Dev)",
    description="Retrieve stored long-term memories for inspection and management. (Dev endpoint)",
)
async def list_user_memories(
    memory_type: MemoryType | None = Query(default=None, description="Filter by memory type"),
    limit: int = Query(default=50, ge=1, le=100, description="Max records to retrieve"),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryResponse]:
    """List persistent memories for user review."""
    return await service.list_memories(memory_type=memory_type, limit=limit)


@user_router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a memory (User Control / Dev)",
    description="Permanently delete a stored memory record. (Dev endpoint)",
)
async def delete_user_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> None:
    """Delete a specific memory by ID."""
    deleted = await service.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found.",
        )

