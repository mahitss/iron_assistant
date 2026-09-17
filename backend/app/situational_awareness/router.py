"""FastAPI REST API router for Situational Awareness, Signal Fusion & Proactive Response Orchestration (Task 60 & Task 99)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.situational_awareness.domain import (
    SignalRecord,
    SituationLifecycleState,
    SituationSeverity,
    SituationTimelineEntry,
    SituationType,
    SourceTrustLevel,
)
from app.situational_awareness.safety import SituationalAwarenessSafetyError
from app.situational_awareness.schemas import (
    AttentionItem,
    CausalHypothesis,
    EventIngestRequest,
    SignalBaseline,
    SignalIngestRequest,
    Situation,
    SituationInvestigateRequest,
    SituationResolveRequest,
    SituationStatsResponse,
    SituationStatus,
    SituationSuppressRequest,
)
from app.situational_awareness.service import situational_awareness_service

router = APIRouter(prefix="/api/situations", tags=["situations"])


# Also define router mounted at /api/v1/situations for backwards compatibility
v1_router = APIRouter(prefix="/api/v1/situations", tags=["situations"])


class EscalateSituationRequest(BaseModel):
    actor: str = "SYSTEM_USER"
    reason: str
    target_severity: SituationSeverity = SituationSeverity.HIGH


class ReopenSituationRequest(BaseModel):
    actor: str = "SYSTEM_USER"
    reason: str = "Situation recurred or new evidence emerged"


# --- Core Ingestion Endpoints ---

@router.post("/signals")
@v1_router.post("/signals")
async def ingest_signal(req: SignalIngestRequest) -> dict[str, Any]:
    """Ingest canonical operational signal for correlation and situation synthesis."""
    try:
        sig = situational_awareness_service._engine.normalizer.normalize_signal(req)
        return await situational_awareness_service.ingest_signal(sig)
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/events")
@v1_router.post("/events")
async def ingest_event(req: EventIngestRequest) -> dict[str, Any]:
    """Legacy Task 60 event ingestion endpoint."""
    try:
        return await situational_awareness_service.ingest_event(req)
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Situations Queries & Filters ---

@router.get("")
@v1_router.get("")
async def list_situations(
    tenant_id: str | None = None,
    project_id: str | None = None,
    lifecycle_state: SituationLifecycleState | None = None,
    situation_type: SituationType | None = None,
    severity: SituationSeverity | None = None,
    unresolved_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """List situations with comprehensive operational filtering and pagination."""
    sits = await situational_awareness_service.list_situations(
        tenant_id=tenant_id,
        project_id=project_id,
        lifecycle_state=lifecycle_state,
        situation_type=situation_type,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    if unresolved_only:
        sits = [
            s for s in sits
            if s.lifecycle_state not in (SituationLifecycleState.RESOLVED, SituationLifecycleState.EXPIRED, SituationLifecycleState.SUPPRESSED)
        ]
    return [s.to_dict() for s in sits]


@router.get("/active")
@v1_router.get("/active")
async def get_active_situations() -> list[dict[str, Any]]:
    """Retrieve all currently active, forming, or escalating situations."""
    sits = await situational_awareness_service.list_situations(limit=200)
    active = [
        s for s in sits
        if s.lifecycle_state in (
            SituationLifecycleState.DETECTED,
            SituationLifecycleState.FORMING,
            SituationLifecycleState.ACTIVE,
            SituationLifecycleState.ESCALATING,
            SituationLifecycleState.INTERVENTION_PENDING,
            SituationLifecycleState.INTERVENTION_ACTIVE,
            SituationLifecycleState.OBSERVING,
            SituationLifecycleState.STABILIZING,
        )
    ]
    return [s.to_dict() for s in active]


@router.get("/summary")
@v1_router.get("/summary")
async def get_situations_summary() -> dict[str, Any]:
    """Retrieve operational summary and statistics of situations."""
    return situational_awareness_service.get_stats()


@router.get("/stats", response_model=SituationStatsResponse)
@v1_router.get("/stats", response_model=SituationStatsResponse)
async def get_situations_stats() -> SituationStatsResponse:
    """Retrieve global situation awareness statistics."""
    data = situational_awareness_service.get_stats()
    return SituationStatsResponse(**data)


@router.get("/attention/feed", response_model=list[AttentionItem])
@v1_router.get("/attention/feed", response_model=list[AttentionItem])
async def get_attention_feed() -> list[AttentionItem]:
    """Retrieve situations prioritized by Attention Engine composite priority."""
    return situational_awareness_service.get_attention_feed()


@router.get("/baselines/catalog", response_model=list[SignalBaseline])
@v1_router.get("/baselines/catalog", response_model=list[SignalBaseline])
async def list_baselines(environment: str | None = None) -> list[SignalBaseline]:
    """List operational metrics baselines."""
    return situational_awareness_service.get_baselines(environment=environment)


@router.get("/audit/trail")
@v1_router.get("/audit/trail")
async def get_audit_trail(
    situation_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Retrieve immutable cryptographic audit trail events."""
    return situational_awareness_service.get_audit_trail(situation_id=situation_id, limit=limit)


# --- Individual Situation Endpoints ---

@router.get("/{situation_id}")
@v1_router.get("/{situation_id}")
async def get_situation(situation_id: str) -> dict[str, Any]:
    """Retrieve a specific situation by ID."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        return sit.to_dict()
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/signals")
@v1_router.get("/{situation_id}/signals")
async def get_situation_signals(situation_id: str) -> list[dict[str, Any]]:
    """Retrieve all signals correlated into a situation."""
    try:
        await situational_awareness_service.get_situation(situation_id)
        signals = situational_awareness_service.get_signals_for_situation(situation_id)
        return [s.to_dict() for s in signals]
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/timeline", response_model=list[SituationTimelineEntry])
@v1_router.get("/{situation_id}/timeline", response_model=list[SituationTimelineEntry])
async def get_situation_timeline(situation_id: str) -> list[SituationTimelineEntry]:
    """Retrieve chronological event timeline distinguishing facts from inferences."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        return sit.timeline
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/evidence")
@v1_router.get("/{situation_id}/evidence")
async def get_situation_evidence(situation_id: str) -> list[dict[str, Any]]:
    """Retrieve evidence items distinguishing OBSERVED, CORRELATED, PREDICTED, and INFERRED."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        return sit.evidence
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/impact")
@v1_router.get("/{situation_id}/impact")
async def get_situation_impact(situation_id: str) -> dict[str, Any]:
    """Retrieve blast radius and plan/goal threat propagation."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        impact = situational_awareness_service._engine.impact_analyzer.calculate_blast_radius(
            situation_id=sit.id,
            affected_resources=sit.affected_resources,
        )
        return impact.model_dump()
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/hypotheses", response_model=list[CausalHypothesis])
@v1_router.get("/{situation_id}/hypotheses", response_model=list[CausalHypothesis])
async def get_situation_hypotheses(situation_id: str) -> list[CausalHypothesis]:
    """Retrieve ranked causal explanations and recommended diagnostics."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        hypotheses = situational_awareness_service._engine.hypotheses_engine.generate_hypotheses(
            situation_id=sit.id,
            events=list(situational_awareness_service._engine._events.values()),
            affected_resources=sit.affected_resources,
        )
        return hypotheses
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/interventions")
@v1_router.get("/{situation_id}/interventions")
async def get_situation_interventions(situation_id: str) -> list[dict[str, Any]]:
    """Retrieve proactive intervention history for situation."""
    try:
        await situational_awareness_service.get_situation(situation_id)
        interventions = [
            iv.to_dict()
            for iv in situational_awareness_service._engine._interventions.values()
            if iv.situation_id == situation_id
        ]
        return interventions
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- Situation Lifecycle Mutation Actions ---

@router.post("/{situation_id}/resolve")
@v1_router.post("/{situation_id}/resolve")
async def resolve_situation(situation_id: str, req: SituationResolveRequest) -> dict[str, Any]:
    """Resolve an incident situation with verified evidence."""
    try:
        sit = await situational_awareness_service.resolve_situation(
            situation_id=situation_id,
            actor=req.actor,
            verification_evidence=req.verification_evidence,
        )
        return sit.to_dict()
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{situation_id}/suppress")
@v1_router.post("/{situation_id}/suppress")
async def suppress_situation(situation_id: str, req: SituationSuppressRequest) -> dict[str, Any]:
    """Suppress a situation with policy-audited reason and expiration."""
    try:
        record = await situational_awareness_service.suppress_situation(
            situation_id=situation_id,
            suppressed_by=req.suppressed_by,
            reason=req.reason,
            duration_seconds=req.duration_seconds,
        )
        return record.to_dict()
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{situation_id}/reopen")
@v1_router.post("/{situation_id}/reopen")
async def reopen_situation(situation_id: str, req: ReopenSituationRequest) -> dict[str, Any]:
    """Reopen a suppressed or resolved situation upon recurrence."""
    try:
        sit = await situational_awareness_service.reopen_situation(
            situation_id=situation_id,
            actor=req.actor,
            reason=req.reason,
        )
        return sit.to_dict()
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{situation_id}/refresh")
@v1_router.post("/{situation_id}/refresh")
async def refresh_situation(situation_id: str) -> dict[str, Any]:
    """Trigger proactive re-deliberation and reality reconciliation check for a situation."""
    try:
        return await situational_awareness_service.orchestrate_situation(situation_id=situation_id)
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{situation_id}/investigate")
@v1_router.post("/{situation_id}/investigate")
async def investigate_situation(situation_id: str, req: SituationInvestigateRequest) -> dict[str, Any]:
    """Dispatch bounded investigation subagent tasks across swarm agents."""
    try:
        return await situational_awareness_service.investigate_situation(
            situation_id=situation_id, scope=req.scope
        )
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{situation_id}/escalate")
@v1_router.post("/{situation_id}/escalate")
async def escalate_situation(situation_id: str, req: EscalateSituationRequest) -> dict[str, Any]:
    """Escalate situation severity and trigger priority recalculation."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        sit.severity = req.target_severity
        situational_awareness_service._engine.lifecycle.transition_situation(
            sit, SituationLifecycleState.ESCALATING, actor=req.actor, reason=req.reason
        )
        return sit.to_dict()
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
