"""REST API endpoints for Kairo Knowledge Fabric."""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.knowledge.backfill import KnowledgeBackfillService
from app.knowledge.ingestion.documents import DocumentIngestionService
from app.knowledge.models import KnowledgeIndexJobModel
from app.knowledge.schemas import (
    DecisionCreate,
    DecisionResponse,
    DecisionSupersedeRequest,
    DocumentUploadResponse,
    IndexingJobResponse,
    KnowledgeEdgeResponse,
    KnowledgeGraphResponse,
    KnowledgeNodeCreate,
    KnowledgeNodeResponse,
    KnowledgeNodeUpdate,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSourceResponse,
    KnowledgeSourceType,
    KnowledgeTimelineResponse,
    KnowledgeType,
)
from app.knowledge.service import KnowledgeFabricService

logger = logging.getLogger("kairo.api.knowledge")

router = APIRouter(prefix="/knowledge", tags=["Knowledge Fabric"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_knowledge_service() -> KnowledgeFabricService:
    """Dependency provider for KnowledgeFabricService."""
    return KnowledgeFabricService()


@router.get(
    "/search",
    response_model=KnowledgeSearchResponse,
    summary="Search Knowledge Fabric",
)
async def search_knowledge(
    q: str = Query(..., min_length=1, description="Search query string"),
    project_id: str | None = Query(default=None, description="Optional project filter"),
    type: KnowledgeType | None = Query(default=None, description="Optional entity type filter"),
    source_type: KnowledgeSourceType | None = Query(default=None, description="Optional provenance source filter"),
    date_from: datetime | None = Query(default=None, description="Start date filter"),
    date_to: datetime | None = Query(default=None, description="End date filter"),
    limit: int = Query(default=15, ge=1, le=50, description="Max results"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse:
    """Hybrid search combining keyword full-text, semantic vectors, recency, and metadata."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    req = KnowledgeSearchRequest(
        query=q,
        project_id=project_id,
        type=type,
        source_type=source_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    results = await service.search(db, user_id=user_id, request=req)
    return KnowledgeSearchResponse(
        query=q,
        total_matches=len(results),
        results=results,
    )


@router.get(
    "/timeline",
    response_model=KnowledgeTimelineResponse,
    summary="Get chronological knowledge timeline",
)
async def get_timeline(
    project_id: str | None = Query(default=None, description="Optional project filter"),
    type: KnowledgeType | None = Query(default=None, description="Optional entity type filter"),
    date_from: datetime | None = Query(default=None, description="Start date"),
    date_to: datetime | None = Query(default=None, description="End date"),
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> KnowledgeTimelineResponse:
    """Assemble chronological timeline of events, decisions, and updates."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    return await service.temporal_reasoner.get_timeline(
        session=db,
        user_id=user_id,
        project_id=project_id,
        type_filter=type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get(
    "/conflicts",
    summary="Detect conflicting claims across workspace knowledge",
)
async def detect_knowledge_conflicts(
    project_id: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> list[dict]:
    """Detect and surface conflicting facts across knowledge nodes."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    return await service.temporal_reasoner.detect_conflicts(
        session=db, user_id=user_id, project_id=project_id
    )


@router.post(
    "/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record architectural or project decision",
)
async def create_decision(
    payload: DecisionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> DecisionResponse:
    """Record an explicit project or architectural decision."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    return await service.record_decision(session=db, user_id=user_id, decision_in=payload)


@router.get(
    "/decisions",
    response_model=list[DecisionResponse],
    summary="List architectural decisions",
)
async def list_decisions(
    project_id: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> list[DecisionResponse]:
    """List decisions for a project or user workspace."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    return await service.list_decisions(session=db, user_id=user_id, project_id=project_id)


@router.post(
    "/decisions/{decision_id}/supersede",
    response_model=DecisionResponse,
    summary="Supersede an existing decision",
)
async def supersede_decision(
    decision_id: str,
    payload: DecisionSupersedeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> DecisionResponse:
    """Supersede a prior decision with a new decision and link via SUPERSEDES edge."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    try:
        return await service.supersede_decision(
            session=db,
            user_id=user_id,
            old_decision_node_id=decision_id,
            new_decision_text=payload.new_decision,
            rationale=payload.rationale,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest document",
)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
) -> DocumentUploadResponse:
    """Validate, parse, chunk, and index an uploaded document into Knowledge Fabric."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    filename = file.filename or "uploaded_document.txt"
    file_bytes = await file.read()

    ingestion_service = DocumentIngestionService()
    try:
        return await ingestion_service.ingest_document(
            session=db,
            user_id=user_id,
            filename=filename,
            file_bytes=file_bytes,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/documents/{job_id}/status",
    response_model=IndexingJobResponse,
    summary="Check document indexing job status",
)
async def get_document_status(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
) -> IndexingJobResponse:
    """Query background document processing status."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    stmt = select(KnowledgeIndexJobModel).where(
        and_(
            KnowledgeIndexJobModel.id == job_id,
            KnowledgeIndexJobModel.user_id == user_id,
        )
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")
    return IndexingJobResponse.model_validate(job)


@router.post(
    "/backfill",
    summary="Trigger idempotent knowledge backfill",
)
async def trigger_backfill(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict:
    """Idempotently index existing memories, projects, and workflows into Knowledge Fabric."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    backfill_svc = KnowledgeBackfillService()
    return await backfill_svc.backfill_all(db, user_id)


@router.get(
    "/{node_id}",
    response_model=KnowledgeNodeResponse,
    summary="Get knowledge node by ID",
)
async def get_node(
    node_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> KnowledgeNodeResponse:
    """Fetch knowledge node with tenant ownership check."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    node = await service.get_node(db, user_id=user_id, node_id=node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge node '{node_id}' not found.")
    return node


@router.get(
    "/{node_id}/relationships",
    response_model=list[KnowledgeEdgeResponse],
    summary="Get node relationships",
)
async def get_node_relationships(
    node_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> list[KnowledgeEdgeResponse]:
    """Fetch incoming and outgoing relationship edges for a node."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    return await service.traversal_service.get_node_relationships(db, user_id=user_id, node_id=node_id)


@router.get(
    "/{node_id}/sources",
    response_model=list[KnowledgeSourceResponse],
    summary="Get node provenance sources",
)
async def get_node_sources(
    node_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> list[KnowledgeSourceResponse]:
    """Fetch provenance source records linked to a node."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    return await service.get_node_sources(db, user_id=user_id, node_id=node_id)


@router.get(
    "/{node_id}/graph",
    response_model=KnowledgeGraphResponse,
    summary="Traverse connected subgraph",
)
async def get_subgraph(
    node_id: str,
    depth: int = Query(default=2, ge=1, le=4),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> KnowledgeGraphResponse:
    """Traverse bounded relationship subgraph starting from node_id."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    try:
        return await service.traversal_service.traverse_subgraph(
            session=db, user_id=user_id, root_node_id=node_id, depth_limit=depth
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge node",
)
async def delete_node(
    node_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_db_session),
    service: KnowledgeFabricService = Depends(get_knowledge_service),
) -> None:
    """Soft-delete knowledge node and cascade clean associations."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    deleted = await service.delete_node(db, user_id=user_id, node_id=node_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge node '{node_id}' not found.")
