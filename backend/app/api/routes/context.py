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
from app.context.universal_schemas import (
    AdaptivePreference,
    AdaptivePreferenceCreate,
    AdaptivePreferenceUpdate,
    ContextHealthMetrics,
    ContextPackage,
    ContextRequest,
    ContextSnapshot,
    PreferenceCategory,
)
from app.context.universal_service import (
    UniversalContextService,
    get_universal_context_service,
)
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


# =====================================================================
# TASK 69: Universal Context & Adaptive Personalization Engine Endpoints
# =====================================================================


def get_current_tenant_id(x_tenant_id: Annotated[str | None, Header()] = None) -> str:
    """Extract tenant ID from request header with default fallback."""
    if not x_tenant_id or not x_tenant_id.strip():
        return "default"
    return x_tenant_id.strip()


@router.post(
    "/build",
    response_model=ContextPackage,
    summary="Build context package",
    description="Execute the 20-step lifecycle to discover, rank, budget, and assemble an authoritative ContextPackage.",
)
async def build_universal_context(
    payload: ContextRequest,
    service: UniversalContextService = Depends(get_universal_context_service),
) -> ContextPackage:
    """Assemble an authoritative ContextPackage."""
    return await service.build_context(payload)


@router.post(
    "/preview",
    response_model=ContextPackage,
    summary="Preview context package",
    description="Assemble a preview ContextPackage without persisting snapshots or cache.",
)
async def preview_universal_context(
    payload: ContextRequest,
    service: UniversalContextService = Depends(get_universal_context_service),
) -> ContextPackage:
    """Preview ContextPackage."""
    return await service.preview_context(payload)


@router.get(
    "/quality",
    summary="Get context quality overview",
    description="Fetch aggregated context quality scores and token metrics.",
)
async def get_context_quality(
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> dict:
    """Get context quality metrics."""
    return service.get_quality_overview(tenant_id)


@router.get(
    "/missing",
    summary="Get detected missing context",
    description="List all identified missing context elements across recent requests.",
)
async def get_missing_context(
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> list[dict]:
    """Get missing context items."""
    return service.get_missing_context(tenant_id)


@router.get(
    "/conflicts",
    summary="Get context conflicts",
    description="List all identified contradictory context assertions.",
)
async def get_context_conflicts(
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> list[dict]:
    """Get context conflicts."""
    return service.get_conflicts(tenant_id)


@router.get(
    "/health",
    response_model=ContextHealthMetrics,
    summary="Get context engine health metrics",
    description="Operational telemetry and health metrics for the universal context engine.",
)
async def get_context_health(
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> ContextHealthMetrics:
    """Get context health metrics."""
    return service.get_health(tenant_id)


@router.get(
    "/preferences",
    response_model=list[AdaptivePreference],
    summary="List adaptive preferences",
    description="List user operational preferences.",
)
async def list_preferences(
    category: PreferenceCategory | None = Query(default=None, description="Optional category filter"),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> list[AdaptivePreference]:
    """List operational preferences."""
    return service.get_preferences(tenant_id=tenant_id, user_id=user_id, category=category)


@router.post(
    "/preferences",
    response_model=AdaptivePreference,
    summary="Register adaptive preference",
    description="Register an explicit or inferred user operational preference.",
)
async def register_preference(
    payload: AdaptivePreferenceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> AdaptivePreference:
    """Register preference."""
    if not payload.tenant_id or payload.tenant_id == "default":
        payload.tenant_id = tenant_id
    return service.register_preference(payload)


@router.patch(
    "/preferences/{preference_id}",
    response_model=AdaptivePreference,
    summary="Update adaptive preference",
)
async def update_preference(
    preference_id: str,
    payload: AdaptivePreferenceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> AdaptivePreference:
    """Update preference."""
    updated = service.update_preference(tenant_id, preference_id, payload)
    if not updated:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Preference not found")
    return updated


@router.delete(
    "/preferences/{preference_id}",
    summary="Delete adaptive preference",
)
async def delete_preference(
    preference_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> dict:
    """Deactivate preference."""
    success = service.delete_preference(tenant_id, preference_id)
    if not success:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Preference not found")
    return {"status": "deleted", "preference_id": preference_id}


@router.get(
    "/snapshots",
    response_model=list[ContextSnapshot],
    summary="List context snapshots",
    description="Retrieve immutable audit snapshots of assembled context.",
)
async def list_snapshots(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> list[ContextSnapshot]:
    """List snapshots."""
    return service.list_snapshots(tenant_id=tenant_id, user_id=user_id, limit=limit)


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=ContextSnapshot,
    summary="Get context snapshot",
)
async def get_snapshot(
    snapshot_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> ContextSnapshot:
    """Get snapshot by ID."""
    snap = service.get_snapshot(tenant_id, snapshot_id)
    if not snap:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snap


@router.get(
    "/snapshots/{snapshot_id}/replay",
    summary="Replay context snapshot",
    description="Reconstruct the exact context items, scores, and explanations from a snapshot.",
)
async def replay_snapshot(
    snapshot_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> dict:
    """Replay snapshot."""
    replay = service.replay_snapshot(tenant_id, snapshot_id)
    if not replay:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Snapshot not found")
    return replay


@router.get(
    "/{context_id}",
    response_model=ContextPackage,
    summary="Get assembled context package",
)
async def get_context_package(
    context_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> ContextPackage:
    """Get context package by ID."""
    pkg = service.get_context(context_id, tenant_id)
    if not pkg:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Context package not found")
    return pkg


@router.get(
    "/{context_id}/explanation",
    summary="Get context inclusion explanation",
)
async def get_context_explanation(
    context_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> dict[str, str]:
    """Get explanations for all items in a context package."""
    return service.get_explanation(context_id, tenant_id)


@router.get(
    "/{context_id}/sources",
    summary="Get context sources and provenance",
)
async def get_context_sources(
    context_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> list[dict]:
    """Get provenance metadata for items in context package."""
    return service.get_sources(context_id, tenant_id)


@router.post(
    "/{context_id}/refresh",
    response_model=ContextPackage,
    summary="Refresh context package",
)
async def refresh_context_package(
    context_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: UniversalContextService = Depends(get_universal_context_service),
) -> ContextPackage:
    """Refresh context package."""
    pkg = await service.refresh_context(context_id, tenant_id)
    if not pkg:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Context package could not be refreshed")
    return pkg
