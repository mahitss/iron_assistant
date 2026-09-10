"""FastAPI REST API router for Knowledge Synthesis & Research Intelligence Engine (Task 63)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.research.safety import ResearchSafetyError
from app.research.schemas import (
    Claim,
    ConflictRecord,
    Document,
    Evidence,
    IngestDocumentRequest,
    KnowledgeGap,
    ResearchRequest,
    Source,
    SynthesisResult,
    VerifyClaimRequest,
)
from app.research.service import research_service

router = APIRouter(prefix="/api/v1/research", tags=["research"])


@router.get("/health")
async def research_health() -> dict[str, str]:
    """Health check endpoint for research intelligence subsystem."""
    return {"status": "ok", "subsystem": "research"}


@router.post("/", response_model=SynthesisResult)
async def execute_research(req: ResearchRequest) -> SynthesisResult:
    """Execute autonomous multi-source knowledge synthesis research session."""
    try:
        return await research_service.execute_research(req)
    except ResearchSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{session_id}")
async def get_research_session(session_id: str) -> dict[str, Any]:
    """Retrieve full details of a research session."""
    sess = research_service.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Research session '{session_id}' not found.")
    return {
        "session_id": session_id,
        "question": sess["request"].question,
        "mode": sess["request"].mode.value,
        "status": sess["status"].value,
        "summary": sess["synthesis"].executive_summary,
        "quality_score": sess["synthesis"].quality_score.model_dump(),
        "established_findings": sess["synthesis"].established_findings,
    }


@router.get("/{session_id}/sources", response_model=list[Source])
async def get_session_sources(session_id: str) -> list[Source]:
    """Retrieve sources evaluated during a research session."""
    return research_service.get_sources(session_id)


@router.get("/{session_id}/claims", response_model=list[Claim])
async def get_session_claims(session_id: str) -> list[Claim]:
    """Retrieve claims extracted during a research session."""
    return research_service.get_claims(session_id)


@router.get("/{session_id}/evidence", response_model=list[Evidence])
async def get_session_evidence(session_id: str) -> list[Evidence]:
    """Retrieve evidence items linked during a research session."""
    return research_service.get_evidence(session_id)


@router.get("/{session_id}/conflicts", response_model=list[ConflictRecord])
async def get_session_conflicts(session_id: str) -> list[ConflictRecord]:
    """Retrieve contradictory assertions detected during a research session."""
    return research_service.get_conflicts(session_id)


@router.get("/{session_id}/gaps", response_model=list[KnowledgeGap])
async def get_session_gaps(session_id: str) -> list[KnowledgeGap]:
    """Retrieve identified knowledge gaps for a research session."""
    return research_service.get_gaps(session_id)


@router.get("/{session_id}/timeline")
async def get_session_timeline(session_id: str) -> dict[str, Any]:
    """Reconstruct historical research trace and timeline replay."""
    try:
        return research_service.replay_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{session_id}/continue", response_model=SynthesisResult)
async def continue_research(session_id: str, follow_up_question: str) -> SynthesisResult:
    """Continue research with a follow-up inquiry incorporating previous findings."""
    sess = research_service.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Research session '{session_id}' not found.")

    req = ResearchRequest(
        question=follow_up_question,
        objective=f"Continuation of {session_id}",
        scope=sess["request"].scope,
        mode=sess["request"].mode,
    )
    return await research_service.execute_research(req)


@router.post("/{session_id}/verify", response_model=Claim)
async def verify_claim(session_id: str, req: VerifyClaimRequest) -> Claim:
    """Verify or refute a claim extracted during research."""
    try:
        return research_service.verify_claim(req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/documents", response_model=Document)
async def ingest_document(req: IngestDocumentRequest) -> Document:
    """Ingest a primary or secondary document into the research registry."""
    try:
        return await research_service.ingest_document(req)
    except ResearchSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/claims/{claim_id}", response_model=Claim)
async def get_claim(claim_id: str) -> Claim:
    """Retrieve specific claim by ID."""
    claim = research_service._engine.claim_extractor.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    return claim


@router.get("/sources/{source_id}", response_model=Source)
async def get_source(source_id: str) -> Source:
    """Retrieve specific source by ID."""
    source = research_service._engine.source_registry.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
    return source


@router.post("/sources/{source_id}/retract")
async def retract_source(source_id: str, reason: str = "Retracted by publisher") -> dict[str, Any]:
    """Retract a source and propagate invalidations to dependent knowledge."""
    try:
        return research_service.retract_source(source_id, reason=reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/")
async def list_research_sessions(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    """List recent research sessions."""
    sessions = []
    for sid, sess in list(research_service._sessions.items())[-limit:]:
        sessions.append(
            {
                "session_id": sid,
                "question": sess["request"].question,
                "mode": sess["request"].mode.value,
                "status": sess["status"].value,
                "summary": sess["synthesis"].executive_summary,
                "quality_score": sess["synthesis"].quality_score.model_dump(),
            }
        )
    return sessions


@router.get("/{session_id}/decision-package")
async def get_decision_package(session_id: str) -> dict[str, Any]:
    """Retrieve decision evidence package for integration with Task 57 Decision Engine."""
    sess = research_service.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Research session '{session_id}' not found.")
    pkg = sess["synthesis"].decision_package
    if not pkg:
        raise HTTPException(status_code=404, detail="Decision package not generated for this session.")
    return pkg.model_dump()


@router.get("/knowledge/claims/{claim_id}", response_model=Claim)
async def get_knowledge_claim(claim_id: str) -> Claim:
    """Retrieve specific claim from knowledge registry."""
    return await get_claim(claim_id)


@router.get("/knowledge/sources/{source_id}", response_model=Source)
async def get_knowledge_source(source_id: str) -> Source:
    """Retrieve specific source from knowledge registry."""
    return await get_source(source_id)


@router.get("/knowledge/changes")
async def get_knowledge_changes(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    """Retrieve history of knowledge changes, invalidations, and decay updates."""
    events = research_service._engine.continuous_engine._change_events
    return [e.model_dump() for e in events[-limit:]]


@router.get("/audit/trail")
async def get_audit_trail(
    session_id: str | None = None,
    source_id: str | None = None,
    claim_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Retrieve tamper-evident cryptographic audit records."""
    return research_service.get_audit_trail(
        session_id=session_id,
        source_id=source_id,
        claim_id=claim_id,
        limit=limit,
    )
