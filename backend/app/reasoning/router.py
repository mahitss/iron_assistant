"""FastAPI REST router for Kairo Autonomous Reasoning & Deliberation Engine (Task 71)."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.reasoning.schemas import (
    ReasoningAssumption,
    ReasoningConclusion,
    ReasoningEvidence,
    ReasoningExplanation,
    ReasoningGraph,
    ReasoningHealthMetrics,
    ReasoningHypothesis,
    ReasoningRequest,
    ReasoningSession,
    ReasoningTraceEvent,
)
from app.reasoning.service import ReasoningEngineService

router = APIRouter(prefix="/reasoning", tags=["Autonomous Reasoning & Deliberation Engine"])


def get_service() -> ReasoningEngineService:
    return ReasoningEngineService.get_instance()


def get_tenant_id(x_tenant_id: Annotated[str | None, Header()] = None) -> str:
    if not x_tenant_id or not x_tenant_id.strip():
        return "default"
    return x_tenant_id.strip()


class InvalidateAssumptionRequest(BaseModel):
    reason: str = Field(..., description="Empirical or operational reason for assumption invalidation")


class AddEvidenceRequest(BaseModel):
    source_type: str = "observation"
    source_id: str = "manual_input"
    content_summary: str
    trust_level: str = "TRUSTED"
    reliability: float = 0.85
    relevance: float = 0.9
    independence_group: str = "manual"
    raw_data: dict[str, Any] = Field(default_factory=dict)


class AbortReasonRequest(BaseModel):
    reason: str = "User aborted deliberation"


@router.post("/start", response_model=ReasoningSession, status_code=status.HTTP_201_CREATED)
async def start_reasoning(
    payload: ReasoningRequest,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
    workspace_id: Annotated[str, Header(alias="X-Workspace-ID")] = "default",
) -> ReasoningSession:
    """Start an autonomous structured reasoning and deliberation session."""
    payload.tenant_id = tenant_id or payload.tenant_id
    payload.workspace_id = workspace_id or payload.workspace_id
    service = get_service()
    return service.start_session(payload)


@router.get("/sessions", response_model=list[ReasoningSession])
async def list_reasoning_sessions(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
    workspace_id: Annotated[str, Header(alias="X-Workspace-ID")] = "default",
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ReasoningSession]:
    """List recent reasoning sessions."""
    service = get_service()
    return service.list_sessions(tenant_id=tenant_id, workspace_id=workspace_id, limit=limit)


@router.get("/health", response_model=ReasoningHealthMetrics)
async def get_health() -> ReasoningHealthMetrics:
    """Retrieve operational telemetry and health metrics for the reasoning engine."""
    service = get_service()
    return service.get_health_metrics()


@router.get("/{reasoning_id}", response_model=ReasoningSession)
async def get_reasoning_session(reasoning_id: str) -> ReasoningSession:
    """Retrieve the complete session state for a given reasoning ID."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")
    return session


@router.get("/{reasoning_id}/hypotheses", response_model=list[ReasoningHypothesis])
async def get_hypotheses(reasoning_id: str) -> list[ReasoningHypothesis]:
    """Retrieve candidate hypotheses, supporting/contradicting evidence, and falsifiers."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")
    return session.hypotheses


@router.get("/{reasoning_id}/evidence", response_model=list[ReasoningEvidence])
async def get_evidence(reasoning_id: str) -> list[ReasoningEvidence]:
    """Retrieve empirical evidence evaluated during deliberation."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")
    return session.evidence


@router.post("/{reasoning_id}/evidence", response_model=ReasoningSession)
async def add_evidence_item(
    reasoning_id: str,
    payload: AddEvidenceRequest,
) -> ReasoningSession:
    """Add empirical evidence into deliberation, triggering falsification and conflict checks."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")

    ev = ReasoningEvidence(
        source_type=payload.source_type,
        source_id=payload.source_id,
        content_summary=payload.content_summary,
        trust_level=payload.trust_level,
        reliability=payload.reliability,
        relevance=payload.relevance,
        independence_group=payload.independence_group,
        raw_data=payload.raw_data,
    )
    return service.add_evidence(reasoning_id, ev)


@router.get("/{reasoning_id}/assumptions", response_model=list[ReasoningAssumption])
async def get_assumptions(reasoning_id: str) -> list[ReasoningAssumption]:
    """Retrieve tracked assumptions and dependent conclusion mappings."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")
    return session.assumptions


@router.post("/{reasoning_id}/assumptions/{assumption_id}/invalidate")
async def invalidate_assumption(
    reasoning_id: str,
    assumption_id: str,
    payload: InvalidateAssumptionRequest,
) -> dict[str, Any]:
    """Invalidate an assumption, automatically cascading to dependent conclusions."""
    service = get_service()
    try:
        session, affected = service.invalidate_assumption(
            reasoning_id=reasoning_id,
            assumption_id=assumption_id,
            reason=payload.reason,
        )
        return {
            "reasoning_id": reasoning_id,
            "assumption_id": assumption_id,
            "invalidated_conclusions": affected,
            "session_confidence": session.confidence.value,
        }
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{reasoning_id}/conclusion", response_model=ReasoningConclusion)
async def get_conclusion(reasoning_id: str) -> ReasoningConclusion:
    """Retrieve synthesized conclusion and epistemic uncertainty state."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session or not session.conclusions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conclusion not found")
    return session.conclusions[0]


@router.get("/{reasoning_id}/explanation", response_model=ReasoningExplanation)
async def get_explanation(reasoning_id: str) -> ReasoningExplanation:
    """Retrieve concise, user-safe explanation (strictly no private chain-of-thought)."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session or not session.explanation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Explanation not found")
    return session.explanation


@router.get("/{reasoning_id}/trace", response_model=list[ReasoningTraceEvent])
async def get_trace(reasoning_id: str) -> list[ReasoningTraceEvent]:
    """Retrieve auditable reasoning trace events without exposing private model deliberations."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")
    return session.trace_events


@router.get("/{reasoning_id}/graph", response_model=ReasoningGraph)
async def get_graph(reasoning_id: str) -> ReasoningGraph:
    """Retrieve the reasoning DAG graph preserving provenance and relationships."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")
    return session.graph


@router.get("/{reasoning_id}/quality")
async def get_reasoning_quality(reasoning_id: str) -> dict[str, Any]:
    """Perform self-audit on deliberation quality, coverage, and calibration (Task 67)."""
    service = get_service()
    session = service.get_session(reasoning_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reasoning session not found")
    return service.integrator.audit_reasoning(session)


@router.get("/{reasoning_id}/replay")
async def replay_deliberation(reasoning_id: str) -> dict[str, Any]:
    """Replay historical deliberation inputs and milestones."""
    service = get_service()
    try:
        return service.replay_session(reasoning_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{reasoning_id}/verify", response_model=ReasoningConclusion)
async def verify_conclusion_endpoint(reasoning_id: str) -> ReasoningConclusion:
    """Submit session conclusion to independent verification (Task 42)."""
    service = get_service()
    try:
        return service.verify_conclusion(reasoning_id)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
