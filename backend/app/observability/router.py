"""FastAPI REST router for Kairo Unified Observability (Task 38)."""

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.observability.schemas import (
    DiagnosticReport,
    HealthScoreSummary,
    Incident,
    IncidentStatus,
    RootCauseAnalysis,
    ServiceMap,
    Trace,
)
from app.observability.service import observability_service

router = APIRouter(prefix="/api/v1/observability", tags=["Observability"])


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str


class ResolveRequest(BaseModel):
    recovery_evidence: str


class TargetRefRequest(BaseModel):
    target_ref: str  # trace_id, task_id


@router.get("/metrics", summary="Prometheus Metrics Exposition")
async def get_metrics() -> Response:
    """Returns application metrics in standard Prometheus text exposition format."""
    prom_text = observability_service.metrics.generate_prometheus_text()
    return Response(content=prom_text, media_type="text/plain; version=0.0.4")


@router.get("/health-score", response_model=HealthScoreSummary, summary="Deterministic Health Score")
async def get_health_score() -> HealthScoreSummary:
    """Returns deterministic system health score with dependency break-down."""
    return observability_service.get_health_score()


@router.get("/traces/{trace_id}", response_model=Trace, summary="Get Distributed Trace")
async def get_trace(
    trace_id: str,
    x_user_id: str | None = Header(default=None),
) -> Trace:
    """Retrieves a distributed trace, enforcing user and project isolation."""
    trace = observability_service.tracer.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    # Enforce user isolation: User A cannot inspect User B traces
    if x_user_id and trace.user_id and trace.user_id != x_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to trace forbidden")

    return trace


@router.get("/tasks/{task_id}", response_model=Trace, summary="Get Task Execution Trace")
async def get_task_trace(
    task_id: str,
    x_user_id: str | None = Header(default=None),
) -> Trace:
    """Retrieves the execution trace for an autonomous task."""
    trace = observability_service.tracer.get_task_trace(task_id)
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task trace not found")

    if x_user_id and trace.user_id and trace.user_id != x_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to task trace forbidden")

    return trace


@router.get("/dependencies", response_model=ServiceMap, summary="Get Dynamic Service Map")
async def get_dependencies() -> ServiceMap:
    """Returns dynamic service dependency graph derived from observed telemetry."""
    return observability_service.dependencies.generate_service_map()


@router.get("/incidents", response_model=list[Incident], summary="List Incidents")
async def list_incidents(
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
) -> list[Incident]:
    """Lists operational incidents with optional status filtering."""
    return observability_service.incidents.list_incidents(status=status_filter)


@router.get("/incidents/{incident_id}", response_model=Incident, summary="Get Incident Details")
async def get_incident(incident_id: str) -> Incident:
    """Retrieves details of an operational incident."""
    inc = observability_service.incidents.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return inc


@router.post("/incidents/{incident_id}/acknowledge", response_model=Incident, summary="Acknowledge Incident")
async def acknowledge_incident(incident_id: str, req: AcknowledgeRequest) -> Incident:
    """Allows an operator to acknowledge an active incident."""
    try:
        return observability_service.incidents.acknowledge_incident(incident_id, req.acknowledged_by)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/incidents/{incident_id}/resolve", response_model=Incident, summary="Resolve Incident with Evidence")
async def resolve_incident(incident_id: str, req: ResolveRequest) -> Incident:
    """Resolves an incident with mandatory supporting recovery evidence."""
    try:
        return observability_service.incidents.resolve_incident(incident_id, req.recovery_evidence)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/diagnose", response_model=DiagnosticReport, summary="User-Safe Diagnostics")
async def run_diagnostics(req: TargetRefRequest) -> DiagnosticReport:
    """Generates user-safe plain English diagnostic report ('What happened?')."""
    try:
        return observability_service.diagnose_trace(req.target_ref)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/root-cause", response_model=RootCauseAnalysis, summary="Root Cause Analysis (Diagnostic Only)")
async def run_root_cause_analysis(req: TargetRefRequest) -> RootCauseAnalysis:
    """Executes evidence-backed root cause analysis on a trace.

    HARD INVARIANT: Diagnostic only; does not perform automated remediation.
    """
    try:
        return observability_service.perform_rca(req.target_ref)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/dashboard", summary="Consolidated Telemetry Dashboard")
async def get_dashboard(
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Returns consolidated telemetry data for frontend observability dashboard."""
    return observability_service.dashboards.get_dashboard_summary(user_id=x_user_id)
