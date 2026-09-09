"""FastAPI endpoints for Kairo RAG V2, Hybrid Retrieval, Grounding, and Knowledge Verification."""

import logging
from typing import Annotated, Any

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
from pydantic import BaseModel, Field

from app.knowledge.rag_orchestrator import RAGOrchestrator
from app.knowledge.schemas import (
    ClassificationLevel,
    HallucinationReport,
    IngestionJob,
    RAGSourceType,
    RetrievalMetrics,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    TrustTier,
)

logger = logging.getLogger("kairo.knowledge.api")

rag_router = APIRouter(tags=["RAG V2 & Grounding"])

# Global singleton orchestrator
_global_rag_orchestrator: RAGOrchestrator | None = None


def get_rag_orchestrator() -> RAGOrchestrator:
    global _global_rag_orchestrator
    if _global_rag_orchestrator is None:
        _global_rag_orchestrator = RAGOrchestrator()
    return _global_rag_orchestrator


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


class IngestTextRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    content_type: str = "text/plain"
    source_type: RAGSourceType = RAGSourceType.USER_UPLOAD
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    trust_tier: TrustTier = TrustTier.USER_PROVIDED
    project_id: str | None = None


class VerifyAnswerRequest(BaseModel):
    generated_answer: str = Field(..., min_length=1)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    results: list[RetrievalResult] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    query: str
    feedback: float = Field(..., ge=-1.0, le=1.0)
    results: list[RetrievalResult] = Field(default_factory=list)


@rag_router.post(
    "/ingest",
    response_model=IngestionJob,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest document or text content into RAG V2 Knowledge Fabric",
)
async def ingest_content(
    payload: IngestTextRequest,
    user_id: str = Depends(get_current_user_id),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> IngestionJob:
    """Ingest raw text or markdown with semantic chunking and embedding."""
    raw_bytes = payload.content.encode("utf-8")
    job = await orchestrator.ingest_content(
        raw_bytes=raw_bytes,
        filename=payload.title,
        content_type=payload.content_type,
        source_type=payload.source_type,
        classification=payload.classification,
        trust_tier=payload.trust_tier,
        project_id=payload.project_id,
        user_id=user_id,
    )
    if job.status == "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=job.error_message)
    return job


@rag_router.post(
    "/upload",
    response_model=IngestionJob,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file (PDF, Markdown, Code, TXT) into RAG V2 Knowledge Fabric",
)
async def upload_file(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    classification: ClassificationLevel = Form(default=ClassificationLevel.INTERNAL),
    trust_tier: TrustTier = Form(default=TrustTier.USER_PROVIDED),
    user_id: str = Depends(get_current_user_id),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> IngestionJob:
    """Upload and ingest arbitrary file bytes into Knowledge Fabric."""
    filename = file.filename or "uploaded_doc.txt"
    content_type = file.content_type or "text/plain"
    file_bytes = await file.read()

    job = await orchestrator.ingest_content(
        raw_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        source_type=RAGSourceType.USER_UPLOAD,
        classification=classification,
        trust_tier=trust_tier,
        project_id=project_id,
        user_id=user_id,
    )
    if job.status == "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=job.error_message)
    return job


@rag_router.post(
    "/search",
    response_model=RetrievalResponse,
    summary="Hybrid search with dense, lexical, code, and graph enrichment",
)
async def search_knowledge(
    request: RetrievalRequest,
    user_id: str = Depends(get_current_user_id),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> RetrievalResponse:
    """Execute hybrid retrieval across dense, sparse, and federated stores."""
    if not request.user_id:
        request.user_id = user_id
    return await orchestrator.retrieve_and_ground(request)


@rag_router.post(
    "/verify",
    response_model=HallucinationReport,
    summary="Verify generated answer grounding against citations",
)
async def verify_answer(
    payload: VerifyAnswerRequest,
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> HallucinationReport:
    """Check hallucination, unsupported claims, and ungrounded statements."""
    return orchestrator.verify_answer(
        generated_answer=payload.generated_answer,
        citations=payload.citations,
        results=payload.results,
    )


@rag_router.post(
    "/feedback",
    status_code=status.HTTP_200_OK,
    summary="Record retrieval feedback for online auto-tuning",
)
async def record_feedback(
    payload: FeedbackRequest,
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> dict[str, str]:
    """Log positive or negative feedback to adapt BM25 vs Vector weights."""
    orchestrator.record_feedback(payload.query, payload.feedback, payload.results)
    return {"status": "ok", "message": "Feedback recorded successfully."}


@rag_router.get(
    "/stats",
    summary="Get Knowledge Fabric and RAG index statistics",
)
async def get_stats(
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> dict[str, Any]:
    """Return indices size, graph nodes/edges, and total documents."""
    return orchestrator.get_stats()


@rag_router.get(
    "/quarantine",
    summary="List quarantined chunks flagged for prompt injection or poisoning",
)
async def get_quarantined_chunks(
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> list[Any]:
    """Inspect quarantined content blocked by the governance filter."""
    return orchestrator.governance.get_quarantined_records()


@rag_router.get(
    "/metrics",
    response_model=RetrievalMetrics,
    summary="Get online evaluation metrics (MRR, HitRate, Grounding Score)",
)
async def get_evaluation_metrics(
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
) -> RetrievalMetrics:
    """Return live evaluation metrics computed by the online learning loop."""
    return orchestrator.get_eval_metrics()
