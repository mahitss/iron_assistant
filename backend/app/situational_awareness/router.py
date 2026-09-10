"""FastAPI REST API router for Situational Awareness & Event Correlation Engine (Task 60)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.situational_awareness.safety import SituationalAwarenessSafetyError
from app.situational_awareness.schemas import (
    AttentionItem,
    CausalHypothesis,
    EventIngestRequest,
    SignalBaseline,
    Situation,
    SituationSeverity,
    SituationStatus,
    SituationTimelineEntry,
)
from app.situational_awareness.service import situational_awareness_service

router = APIRouter(prefix="/api/v1/situations", tags=["situations"])


# Request Schemas
class ResolveSituationRequest(BaseModel):
    actor: str = "SYSTEM_USER"
    verification_evidence: dict[str, Any] = Field(default_factory=dict)


class EscalateSituationRequest(BaseModel):
    actor: str = "SYSTEM_USER"
    reason: str
    target_severity: SituationSeverity = SituationSeverity.HIGH


# Endpoints
@router.post("/events")
async def ingest_event(req: EventIngestRequest) -> dict[str, Any]:
    """Ingest, normalize, deduplicate, correlate, and update/create operational situations."""
    try:
        return await situational_awareness_service.ingest_event(req)
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[Situation])
async def list_situations(
    environment: str | None = None,
    status: SituationStatus | None = None,
) -> list[Situation]:
    """List active or historical situations."""
    return await situational_awareness_service.list_situations(environment=environment, status=status)


@router.get("/attention/feed", response_model=list[AttentionItem])
async def get_attention_feed() -> list[AttentionItem]:
    """Retrieve situations prioritized by severity, blast radius, and urgency."""
    return situational_awareness_service.get_attention_feed()


@router.get("/baselines/catalog", response_model=list[SignalBaseline])
async def list_baselines(environment: str | None = None) -> list[SignalBaseline]:
    """List operational metrics baselines and statistical calibration states."""
    return situational_awareness_service.get_baselines(environment=environment)


@router.get("/audit/trail")
async def get_audit_trail(
    situation_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Retrieve immutable cryptographic audit trail events."""
    return situational_awareness_service.get_audit_trail(situation_id=situation_id, limit=limit)


@router.get("/{situation_id}", response_model=Situation)
async def get_situation(situation_id: str) -> Situation:
    """Retrieve a specific situation by ID."""
    try:
        return await situational_awareness_service.get_situation(situation_id)
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/timeline", response_model=list[SituationTimelineEntry])
async def get_situation_timeline(situation_id: str) -> list[SituationTimelineEntry]:
    """Retrieve chronological event timeline distinguishing facts from inferences."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        return sit.timeline
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/impact")
async def get_situation_impact(situation_id: str) -> dict[str, Any]:
    """Retrieve blast radius and plan/goal threat propagation."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        impact = situational_awareness_service._engine.impact_analyzer.calculate_blast_radius(
            situation_id=sit.situation_id,
            affected_resources=sit.affected_resources,
        )
        return impact.model_dump()
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{situation_id}/hypotheses", response_model=list[CausalHypothesis])
async def get_situation_hypotheses(situation_id: str) -> list[CausalHypothesis]:
    """Retrieve ranked causal explanations and recommended diagnostics."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        return sit.hypotheses
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{situation_id}/resolve", response_model=Situation)
async def resolve_situation(situation_id: str, req: ResolveSituationRequest) -> Situation:
    """Resolve an incident situation with verified evidence."""
    try:
        return await situational_awareness_service.resolve_situation(
            situation_id=situation_id,
            actor=req.actor,
            verification_evidence=req.verification_evidence,
        )
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{situation_id}/escalate", response_model=Situation)
async def escalate_situation(situation_id: str, req: EscalateSituationRequest) -> Situation:
    """Escalate situation severity and trigger priority recalculation."""
    try:
        sit = await situational_awareness_service.get_situation(situation_id)
        sit.severity = req.target_severity
        situational_awareness_service._engine.auditor.record_event(
            event_type="SITUATION_ESCALATED",
            actor=req.actor,
            situation_id=situation_id,
            details={"target_severity": req.target_severity.value, "reason": req.reason},
        )
        return sit
    except SituationalAwarenessSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
