"""FastAPI router exposing authoritative REST endpoints for the Capability Lifecycle Engine (Task 91 Phase 20)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.capability_lifecycle.models import (
    CanaryRolloutConfig,
    CanaryRolloutState,
    CapabilityMetadata,
    CapabilityVersionRecord,
    CompatibilityReport,
    ConformanceTestResult,
    ConformanceTestVector,
    DeprecationPlan,
    HealthStatus,
    LifecycleState,
    LifecycleTransitionEvent,
    PromotionGateEvaluation,
    RollbackRecord,
    SimulationStatus,
)
from app.capability_lifecycle.service import (
    CapabilityLifecycleService,
    get_capability_lifecycle_service,
)

router = APIRouter(prefix="/api/v1/capabilities", tags=["Capability Lifecycle"])


class DiscoverCapabilityRequest(BaseModel):
    capability_id: str = Field(..., description="Unique stable capability ID")
    name: str
    description: str
    capability_type: str = "TOOL"
    version: str = "1.0.0"
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    required_permissions: List[str] = Field(default_factory=lambda: ["READ"])
    memory_mb: float = 128.0
    timeout_seconds: float = 30.0


class CanaryStartRequest(BaseModel):
    target_version: str
    canary_percent: float = 5.0
    canary_duration_seconds: float = 60.0
    error_rate_threshold: float = 0.05


class PromoteRequest(BaseModel):
    target_version: str
    actor: str = "operator"


class RollbackRequest(BaseModel):
    target_version: Optional[str] = None
    reason: str = "Operator requested rollback"
    actor: str = "operator"


class DeprecateRequest(BaseModel):
    reason: str
    replacement_capability_id: Optional[str] = None
    migration_guidance: str = ""
    sunset_days: int = 30
    actor: str = "operator"


class RetireRequest(BaseModel):
    force: bool = False
    actor: str = "operator"


# ==============================================================================
# READ ENDPOINTS
# ==============================================================================

@router.get("", response_model=List[CapabilityMetadata])
async def list_capabilities(
    state: Optional[LifecycleState] = None,
    health: Optional[HealthStatus] = None,
) -> List[CapabilityMetadata]:
    """List all registered capabilities, optionally filtered by state or health."""
    svc = get_capability_lifecycle_service()
    caps = svc.list_capabilities()
    if state:
        caps = [c for c in caps if c.lifecycle_state == state]
    if health:
        caps = [c for c in caps if c.health_state == health]
    return caps


@router.get("/{capability_id}", response_model=CapabilityMetadata)
async def get_capability(capability_id: str) -> CapabilityMetadata:
    """Retrieve full capability metadata by ID."""
    svc = get_capability_lifecycle_service()
    cap = svc.get_capability(capability_id)
    if not cap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability '{capability_id}' not found")
    return cap


@router.get("/{capability_id}/versions", response_model=List[CapabilityVersionRecord])
async def get_capability_versions(capability_id: str) -> List[CapabilityVersionRecord]:
    """List all immutable version records for the given capability."""
    svc = get_capability_lifecycle_service()
    if not svc.get_capability(capability_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability '{capability_id}' not found")
    return svc.version_manager.list_versions(capability_id)


@router.get("/{capability_id}/health")
async def get_capability_health(capability_id: str) -> Dict[str, Any]:
    """Retrieve operational health, reliability metrics, and failure counters."""
    svc = get_capability_lifecycle_service()
    cap = svc.get_capability(capability_id)
    if not cap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability '{capability_id}' not found")
    return {
        "capability_id": cap.capability_id,
        "health_state": cap.health_state.value,
        "lifecycle_state": cap.lifecycle_state.value,
        "reliability": cap.reliability.model_dump(),
    }


@router.get("/{capability_id}/dependencies")
async def get_capability_dependencies(capability_id: str) -> Dict[str, Any]:
    """Retrieve forward dependencies and reverse dependents (impact analysis)."""
    svc = get_capability_lifecycle_service()
    cap = svc.get_capability(capability_id)
    if not cap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability '{capability_id}' not found")
    return {
        "capability_id": cap.capability_id,
        "dependencies": [d.model_dump() for d in svc.dependency_graph.get_dependencies(capability_id)],
        "dependents": svc.dependency_graph.get_dependents(capability_id),
        "transitive_dependents": list(svc.dependency_graph.get_transitive_dependents(capability_id)),
    }


@router.get("/{capability_id}/lifecycle", response_model=List[LifecycleTransitionEvent])
async def get_lifecycle_history(capability_id: str) -> List[LifecycleTransitionEvent]:
    """Retrieve the chronological lifecycle transition event history."""
    svc = get_capability_lifecycle_service()
    if not svc.get_capability(capability_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability '{capability_id}' not found")
    return svc.state_machine.get_events_for_capability(capability_id)


# ==============================================================================
# MUTATING WORKFLOW ENDPOINTS
# ==============================================================================

@router.post("/discover", response_model=CapabilityMetadata, status_code=status.HTTP_201_CREATED)
async def discover_capability(req: DiscoverCapabilityRequest) -> CapabilityMetadata:
    """Ingest and register a newly discovered capability."""
    svc = get_capability_lifecycle_service()
    meta = CapabilityMetadata(
        capability_id=req.capability_id,
        name=req.name,
        description=req.description,
        capability_type=req.capability_type,
        version=req.version,
        parameters_schema=req.parameters_schema,
        output_schema=req.output_schema,
        required_permissions=req.required_permissions,
    )
    meta.resource_profile.memory_mb = req.memory_mb
    meta.resource_profile.timeout_seconds = req.timeout_seconds
    return svc.register_discovered_capability(meta)


@router.post("/{capability_id}/validate")
async def validate_capability(capability_id: str) -> Dict[str, Any]:
    """Run formal validation pipeline on capability."""
    svc = get_capability_lifecycle_service()
    passed, issues = svc.validate_capability(capability_id)
    return {"capability_id": capability_id, "passed": passed, "issues": issues}


@router.post("/{capability_id}/conformance", response_model=ConformanceTestResult)
async def test_conformance(capability_id: str) -> ConformanceTestResult:
    """Execute deterministic conformance test vectors."""
    svc = get_capability_lifecycle_service()
    try:
        return svc.test_conformance(capability_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{capability_id}/simulate")
async def simulate_rollout(capability_id: str) -> Dict[str, Any]:
    """Simulate candidate rollout consequences against Task 89 digital twin sandbox."""
    svc = get_capability_lifecycle_service()
    try:
        stat, details = svc.simulate_rollout(capability_id)
        return {"capability_id": capability_id, "simulation_status": stat.value, "details": details}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{capability_id}/canary", response_model=CanaryRolloutState)
async def start_canary(capability_id: str, req: CanaryStartRequest) -> CanaryRolloutState:
    """Initiate a canary rollout with progressive traffic routing."""
    svc = get_capability_lifecycle_service()
    cfg = CanaryRolloutConfig(
        canary_percent=req.canary_percent,
        canary_duration_seconds=req.canary_duration_seconds,
        error_rate_threshold=req.error_rate_threshold,
    )
    try:
        return svc.start_canary(capability_id, target_version=req.target_version, config=cfg)
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(re))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/{capability_id}/promote")
async def promote_capability(capability_id: str, req: PromoteRequest) -> Dict[str, Any]:
    """Evaluate all 11 gates and promote the capability version to ACTIVE."""
    svc = get_capability_lifecycle_service()
    try:
        promoted, err, gates = svc.promote_capability(
            capability_id, target_version=req.target_version, actor=req.actor
        )
        if not promoted:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=err)
        return {"capability_id": capability_id, "promoted": True, "version": req.target_version, "gates": gates.gates}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/{capability_id}/rollback")
async def rollback_capability(capability_id: str, req: RollbackRequest) -> Dict[str, Any]:
    """Revert capability to previous stable version with health check."""
    svc = get_capability_lifecycle_service()
    try:
        ok, rec, msg = svc.rollback_capability(
            capability_id, target_version=req.target_version, reason=req.reason, actor=req.actor
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        return {"capability_id": capability_id, "success": ok, "record": rec.model_dump(), "message": msg}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/{capability_id}/deprecate", response_model=DeprecationPlan)
async def deprecate_capability(capability_id: str, req: DeprecateRequest) -> DeprecationPlan:
    """Mark capability as DEPRECATED with a sunset deadline and replacement advisory."""
    svc = get_capability_lifecycle_service()
    try:
        return svc.deprecate_capability(
            capability_id,
            reason=req.reason,
            replacement_capability_id=req.replacement_capability_id,
            migration_guidance=req.migration_guidance,
            sunset_days=req.sunset_days,
            actor=req.actor,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/{capability_id}/retire")
async def retire_capability(capability_id: str, req: RetireRequest) -> Dict[str, Any]:
    """Retire capability permanently (fails if active consumers exist unless force=True)."""
    svc = get_capability_lifecycle_service()
    try:
        ok, msg = svc.retire_capability(capability_id, force_retirement=req.force, actor=req.actor)
        if not ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        return {"capability_id": capability_id, "retired": True, "message": msg}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
