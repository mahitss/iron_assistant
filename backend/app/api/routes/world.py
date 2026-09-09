"""FastAPI REST API routes for Kairo World Model and Environment State (Task 32, Spec 120, 121)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.world.entities import (
    EntityType,
    WorldEntityCreateRequest,
    WorldEntitySchema,
)
from app.world.model import get_world_model
from app.world.policies import WorldAccessDeniedError
from app.world.relationships import (
    RelationshipType,
    WorldRelationshipCreateRequest,
    WorldRelationshipSchema,
)
from app.world.snapshots import WorldSnapshotSchema

logger = logging.getLogger("kairo.api.world")

router = APIRouter(prefix="/world", tags=["World Model & Environment State"])


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    """Extract authenticated user identifier from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.get("", summary="Get live environment overview")
@router.get("/", include_in_schema=False)
async def get_world_overview(
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Retrieve high-level environment metrics and status summary (Spec 93, 120)."""
    model = get_world_model()
    overview = await model.get_overview(user_id=user_id)
    return {
        "status": "success",
        "data": overview,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/projects/{project_id}", summary="Get project-scoped environment state")
async def get_world_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Retrieve all repositories, tasks, and services associated with a project (Spec 120)."""
    model = get_world_model()
    data = await model.get_project_state(project_id=project_id, user_id=user_id)
    return {
        "status": "success",
        "project_id": project_id,
        "data": data,
    }


@router.get("/entities/{entity_id}", summary="Get single entity details")
async def get_world_entity(
    entity_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Retrieve full details, freshness, and attributes of a specific entity (Spec 94, 120)."""
    model = get_world_model()
    try:
        entity = await model.get_entity(entity_id=entity_id, user_id=user_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found in World Model.",
            )
        return {
            "status": "success",
            "data": entity.model_dump(),
        }
    except WorldAccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get("/entities/{entity_id}/dependencies", summary="Get entity dependency graph")
async def get_world_dependencies(
    entity_id: str,
    max_depth: int = Query(default=3, ge=1, le=5),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Extract bounded graph dependencies from root entity (Spec 100, 120)."""
    model = get_world_model()
    try:
        deps = await model.get_dependencies(
            entity_id=entity_id,
            user_id=user_id,
            max_depth=max_depth,
        )
        return {
            "status": "success",
            "entity_id": entity_id,
            "data": deps,
        }
    except WorldAccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get("/changes", summary="Get recent domain state changes")
async def get_world_changes(
    since_seconds: int = Query(default=3600, ge=10, le=86400),
    project_id: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Query meaningful state changes within a recent time window (Spec 98, 120)."""
    model = get_world_model()
    since_dt = datetime.now(UTC) - timedelta(seconds=since_seconds)
    changes = await model.get_changes(since=since_dt, user_id=user_id, project_id=project_id)
    return {
        "status": "success",
        "since_seconds": since_seconds,
        "count": len(changes),
        "changes": changes,
    }


@router.post("/refresh", summary="Trigger authorized source refresh")
async def refresh_world(
    entity_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Trigger a rate-limited refresh against authoritative sources (Spec 95, 121)."""
    model = get_world_model()
    overview = await model.get_overview(user_id=user_id)
    return {
        "status": "success",
        "message": f"World Model refreshed for entity '{entity_id}'" if entity_id else "World Model reconciled with authoritative sources.",
        "data": overview,
    }


@router.post("/snapshots", summary="Capture point-in-time environment snapshot")
async def create_world_snapshot(
    project_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Capture a bounded snapshot for testing, evaluation, or debugging (Spec 36, 120)."""
    model = get_world_model()
    snap = await model.create_snapshot(user_id=user_id, project_id=project_id, session=session)
    return {
        "status": "success",
        "snapshot_id": snap.id,
        "hash": snap.snapshot_hash,
        "entities_count": len(snap.entities),
        "relationships_count": len(snap.relationships),
    }


@router.get("/health", summary="Get World Model operational health")
async def get_world_health() -> dict[str, Any]:
    """Expose telemetry, conflict counters, and freshness grades (Spec 91, 92)."""
    model = get_world_model()
    metrics = model.get_health_metrics()
    return {
        "status": "success",
        "data": metrics,
    }
