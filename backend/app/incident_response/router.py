"""FastAPI REST API router for Incident Response & Recovery Autonomy Engine (Task 61)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.incident_response.safety import IncidentResponseSafetyError
from app.incident_response.schemas import (
    AddEvidenceRequest,
    ApproveActionRequest,
    CreateIncidentFromSituationRequest,
    IncidentResponse,
    IncidentStatus,
    PostmortemReport,
    ResolveIncidentRequest,
    TriageIncidentRequest,
    VerifyRecoveryRequest,
)
from app.incident_response.service import incident_response_service

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


class ReopenIncidentRequest(BaseModel):
    actor: str = "SYSTEM_USER"
    reason: str = "Recurrence of symptoms observed"


class SelectOptionRequest(BaseModel):
    actor: str = "INCIDENT_COMMANDER"


@router.get("/health")
async def incident_health() -> dict[str, str]:
    """Health check for Incident Response subsystem."""
    return {"status": "ok", "subsystem": "incident_response"}


@router.post("/from-situation", response_model=IncidentResponse)
async def create_incident_from_situation(req: CreateIncidentFromSituationRequest) -> IncidentResponse:
    """Initialize an operational incident response cycle from a situation."""
    try:
        return await incident_response_service.create_incident_from_situation(req)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    environment: str | None = None,
    status: IncidentStatus | None = None,
) -> list[IncidentResponse]:
    """List operational incidents."""
    return await incident_response_service.list_incidents(environment=environment, status=status)


@router.get("/audit/trail")
async def get_audit_trail(
    incident_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Retrieve immutable cryptographic audit trail events."""
    return incident_response_service.get_audit_trail(incident_id=incident_id, limit=limit)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str) -> IncidentResponse:
    """Retrieve a specific incident by ID."""
    try:
        return await incident_response_service.get_incident(incident_id)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{incident_id}/triage", response_model=IncidentResponse)
async def triage_incident(incident_id: str, req: TriageIncidentRequest) -> IncidentResponse:
    """Apply triage adjustments to severity and urgency."""
    try:
        return await incident_response_service.triage_incident(incident_id, req)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{incident_id}/evidence", response_model=IncidentResponse)
async def add_evidence(incident_id: str, req: AddEvidenceRequest) -> IncidentResponse:
    """Attach supporting or contradictory evidence to a candidate hypothesis."""
    try:
        return await incident_response_service.add_evidence(incident_id, req)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{incident_id}/options/{option_id}/select", response_model=IncidentResponse)
async def select_option(incident_id: str, option_id: str, req: SelectOptionRequest) -> IncidentResponse:
    """Select a candidate response strategy and prepare mitigation action."""
    try:
        return await incident_response_service.select_option(incident_id, option_id, actor=req.actor)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{incident_id}/actions/approve", response_model=IncidentResponse)
async def approve_action(incident_id: str, req: ApproveActionRequest) -> IncidentResponse:
    """Approve a pending high-impact action."""
    try:
        return await incident_response_service.approve_action(incident_id, req)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{incident_id}/checkpoints/verify", response_model=IncidentResponse)
async def verify_checkpoint(incident_id: str, req: VerifyRecoveryRequest) -> IncidentResponse:
    """Validate recovery checkpoint barrier."""
    try:
        return await incident_response_service.verify_checkpoint(incident_id, req)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(incident_id: str, req: ResolveIncidentRequest) -> IncidentResponse:
    """Resolve an incident with verified recovery evidence and generate blameless postmortem."""
    try:
        return await incident_response_service.resolve_incident(incident_id, req)
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{incident_id}/reopen", response_model=IncidentResponse)
async def reopen_incident(incident_id: str, req: ReopenIncidentRequest) -> IncidentResponse:
    """Reopen a resolved incident upon symptom recurrence."""
    try:
        return await incident_response_service.reopen_incident(
            incident_id, actor=req.actor, reason=req.reason
        )
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{incident_id}/postmortem", response_model=PostmortemReport | None)
async def get_postmortem(incident_id: str) -> PostmortemReport | None:
    """Retrieve postmortem report for a resolved incident."""
    try:
        inc = await incident_response_service.get_incident(incident_id)
        return inc.postmortem
    except IncidentResponseSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
