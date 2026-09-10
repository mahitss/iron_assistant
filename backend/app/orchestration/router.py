"""FastAPI REST API router for Kairo Resource & Capability Orchestration Engine (Task 59)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.orchestration.safety import (
    AuthorizationMissingError,
    CapabilityUnavailableError,
    OrchestrationSafetyError,
    ResourceContentionError,
    StaleOrchestrationError,
)
from app.orchestration.schemas import (
    CapabilityDefinition,
    CapabilityStatus,
    OrchestrationPlan,
    OrchestrationStatus,
    ProviderAssignment,
    ResourceDefinition,
    ResourceReservation,
    ResourceType,
)
from app.orchestration.service import orchestration_service

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


# Request Schemas
class AnalyzeRequest(BaseModel):
    tasks: list[dict[str, Any]]
    environment: str = "development"
    granted_permissions: list[str] = Field(default_factory=list)


class CreateOrchestrationRequest(BaseModel):
    name: str
    tasks: list[dict[str, Any]]
    strategic_plan_id: str | None = None
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    environment: str = "development"
    granted_permissions: list[str] = Field(default_factory=list)
    actor: str = "SYSTEM_USER"


class ReserveResourceRequest(BaseModel):
    resource_id: str
    owner: str
    purpose: str
    amount: float = 1.0
    expires_at: datetime
    scope: str = "GLOBAL"


class ReleaseReservationRequest(BaseModel):
    reservation_id: str


class RevalidateRequest(BaseModel):
    environment: str = "development"
    active_permissions: list[str] = Field(default_factory=list)
    unhealthy_providers: list[str] = Field(default_factory=list)


class FailoverRequest(BaseModel):
    task_id: str
    error_message: str
    actor: str = "SYSTEM_USER"


# Endpoints
@router.post("/analyze")
async def analyze_orchestration(req: AnalyzeRequest) -> dict[str, Any]:
    """Perform pre-execution gap analysis: capabilities, resources, permissions, and feasibility."""
    try:
        return await orchestration_service.analyze(
            tasks=req.tasks,
            environment=req.environment,
            granted_permissions=set(req.granted_permissions),
        )
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_model=OrchestrationPlan)
async def create_orchestration_plan(req: CreateOrchestrationRequest) -> OrchestrationPlan:
    """Transform tasks into a fully mapped OrchestrationPlan."""
    try:
        return await orchestration_service.create_orchestration_plan(
            name=req.name,
            tasks=req.tasks,
            strategic_plan_id=req.strategic_plan_id,
            dependencies=req.dependencies,
            environment=req.environment,
            granted_permissions=set(req.granted_permissions),
            actor=req.actor,
        )
    except CapabilityUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationMissingError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ResourceContentionError, OrchestrationSafetyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/catalog/capabilities", response_model=list[CapabilityDefinition])
async def list_capabilities(
    environment: str | None = None,
    status: CapabilityStatus | None = None,
) -> list[CapabilityDefinition]:
    """List registered capabilities in the system catalog."""
    return await orchestration_service.get_capabilities(environment=environment, status=status)


@router.get("/catalog/resources", response_model=list[ResourceDefinition])
async def list_resources(
    environment: str | None = None,
    resource_type: ResourceType | None = None,
) -> list[ResourceDefinition]:
    """List available resources, quotas, and capacity metrics."""
    return await orchestration_service.get_resources(environment=environment, resource_type=resource_type)


@router.post("/resources/reserve", response_model=ResourceReservation)
async def reserve_resource(req: ReserveResourceRequest) -> ResourceReservation:
    """Create a time-bounded resource reservation."""
    try:
        return await orchestration_service.reserve_resource(
            resource_id=req.resource_id,
            owner=req.owner,
            purpose=req.purpose,
            amount=req.amount,
            expires_at=req.expires_at,
            scope=req.scope,
        )
    except ResourceContentionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resources/release")
async def release_reservation(req: ReleaseReservationRequest) -> dict[str, Any]:
    """Release a resource reservation and restore capacity."""
    success = await orchestration_service.release_reservation(req.reservation_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Reservation '{req.reservation_id}' not found or already inactive.")
    return {"status": "RELEASED", "reservation_id": req.reservation_id}


@router.get("/list", response_model=list[OrchestrationPlan])
async def list_orchestration_plans(
    status: OrchestrationStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OrchestrationPlan]:
    """List recent orchestration plans."""
    return await orchestration_service.list_orchestrations(status=status, limit=limit)


@router.get("/{orchestration_id}", response_model=OrchestrationPlan)
async def get_orchestration_plan(orchestration_id: str) -> OrchestrationPlan:
    """Retrieve an orchestration plan by ID."""
    try:
        return await orchestration_service.get_orchestration_plan(orchestration_id)
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{orchestration_id}/assignments", response_model=list[ProviderAssignment])
async def get_plan_assignments(orchestration_id: str) -> list[ProviderAssignment]:
    """Retrieve task-to-provider assignments for an orchestration plan."""
    try:
        plan = await orchestration_service.get_orchestration_plan(orchestration_id)
        return plan.assignments
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{orchestration_id}/topology")
async def get_plan_topology(orchestration_id: str) -> dict[str, Any]:
    """Retrieve execution graph topology, waves, and synchronization barriers."""
    try:
        plan = await orchestration_service.get_orchestration_plan(orchestration_id)
        return {
            "orchestration_id": plan.orchestration_id,
            "task_graph": plan.task_graph,
            "execution_waves": plan.execution_waves,
            "synchronization_points": plan.synchronization_points,
            "verification_points": plan.verification_points,
            "fallback_paths": plan.fallback_paths,
        }
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{orchestration_id}/revalidate")
async def revalidate_plan(orchestration_id: str, req: RevalidateRequest) -> dict[str, Any]:
    """Revalidate plan before execution against environmental drift."""
    try:
        is_valid = await orchestration_service.revalidate(
            orchestration_id=orchestration_id,
            current_environment=req.environment,
            active_permissions=set(req.active_permissions),
        )
        return {"status": "VALIDATED", "is_valid": is_valid}
    except StaleOrchestrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{orchestration_id}/failover")
async def trigger_plan_failover(orchestration_id: str, req: FailoverRequest) -> dict[str, Any]:
    """Trigger failover for a failed task to secondary/emergency fallback."""
    try:
        return await orchestration_service.trigger_failover(
            orchestration_id=orchestration_id,
            task_id=req.task_id,
            error_message=req.error_message,
            actor=req.actor,
        )
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{orchestration_id}/health")
async def get_plan_health(orchestration_id: str) -> dict[str, Any]:
    """Get operational health status and resource leak audit report."""
    try:
        plan = await orchestration_service.get_orchestration_plan(orchestration_id)
        leaks = orchestration_service._engine.resource_registry.detect_leaks()
        return {
            "orchestration_id": plan.orchestration_id,
            "status": plan.status.value,
            "health": plan.health.value,
            "detected_leaks": leaks,
            "is_clean": len(leaks) == 0,
        }
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/explain/{task_id}")
async def explain_task_assignment(task_id: str) -> dict[str, Any]:
    """Explain why a specific provider and resource allocation was selected for a task."""
    return orchestration_service.explain_task(task_id)


@router.get("/audit/trail")
async def get_audit_trail(
    orchestration_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Retrieve immutable cryptographic audit trail events."""
    return orchestration_service.get_audit_trail(orchestration_id=orchestration_id, limit=limit)
