"""FastAPI Router for Kairo Environmental Intelligence & Digital Twin Engine (Task 54)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.environment.safety import (
    FalseTopologyError,
    FutureLeakageError,
    RemediationLoopError,
    SecretStorageViolationError,
    UnverifiedRollbackError,
)
from app.environment.schemas import (
    ChangeType,
    DriftType,
    HealthEvidence,
    ImpactLevel,
    NodeType,
    RelationshipConfidence,
    RelationshipType,
    ScopeType,
)
from app.environment.service import environment_service

router = APIRouter(prefix="/api/v1/environment", tags=["Environmental Intelligence & Digital Twin"])


# Request Models
class RegisterNodeRequest(BaseModel):
    node_id: str
    node_type: NodeType
    canonical_id: str
    display_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None
    status: str = "UNKNOWN"
    confidence: float = 1.0


class RegisterEdgeRequest(BaseModel):
    source: str
    relationship: RelationshipType
    target: str
    confidence: RelationshipConfidence = RelationshipConfidence.OBSERVED
    provenance: dict[str, Any] = Field(default_factory=dict)
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None
    is_same_environment_only: bool = False


class RecordHealthRequest(BaseModel):
    node_id: str
    evidences: list[HealthEvidence] = Field(default_factory=list)
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None


class RecordChangeRequest(BaseModel):
    resource_id: str
    change_type: ChangeType
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    source: str
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None


class RecordDriftRequest(BaseModel):
    resource_id: str
    drift_type: DriftType
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class CreateIncidentRequest(BaseModel):
    scope: ScopeType = ScopeType.SYSTEM
    symptoms: list[str] = Field(default_factory=list)
    affected_resources: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    suspected_cause: str | None = None
    root_cause: str | None = None
    scope_id: str | None = None


class WhatIfRequest(BaseModel):
    target_node_id: str
    event: str = "service_outage"
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None


class ProposeRemediationRequest(BaseModel):
    target: str
    current_state: dict[str, Any] = Field(default_factory=dict)
    desired_state: dict[str, Any] = Field(default_factory=dict)
    risk: ImpactLevel = ImpactLevel.MEDIUM
    dependencies: list[str] = Field(default_factory=list)
    rollback_target: dict[str, Any] | None = None
    rollback_verified: bool = False
    is_production: bool = False


class AutoHealRequest(BaseModel):
    resource_id: str
    plan_id: str
    is_pre_authorized: bool = True


# Endpoints
@router.get("/twin")
def get_digital_twin(
    scope: ScopeType = Query(ScopeType.SYSTEM),
    scope_id: str | None = Query(None),
) -> dict[str, Any]:
    twin = environment_service.get_or_create_twin(scope=scope, scope_id=scope_id)
    return {
        "twin_id": twin.twin_id,
        "scope": twin.scope.value,
        "scope_id": twin.scope_id,
        "version": twin.version,
        "timestamp": twin.timestamp.isoformat(),
        "nodes_count": len(twin.nodes),
        "edges_count": len(twin.edges),
        "freshness": twin.freshness.value,
        "confidence": twin.confidence,
    }


@router.post("/nodes")
def register_node(req: RegisterNodeRequest) -> dict[str, Any]:
    try:
        node = environment_service.register_node(
            node_id=req.node_id,
            node_type=req.node_type,
            canonical_id=req.canonical_id,
            display_name=req.display_name,
            metadata=req.metadata,
            scope=req.scope,
            scope_id=req.scope_id,
            status=req.status,
            confidence=req.confidence,
        )
        return {"status": "success", "node": node.model_dump()}
    except SecretStorageViolationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/edges")
def register_edge(req: RegisterEdgeRequest) -> dict[str, Any]:
    try:
        edge = environment_service.register_edge(
            source=req.source,
            relationship=req.relationship,
            target=req.target,
            confidence=req.confidence,
            provenance=req.provenance,
            scope=req.scope,
            scope_id=req.scope_id,
            is_same_environment_only=req.is_same_environment_only,
        )
        return {"status": "success", "edge": edge.model_dump()}
    except FalseTopologyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/health")
def record_health(req: RecordHealthRequest) -> dict[str, Any]:
    record = environment_service.record_node_health(
        node_id=req.node_id,
        evidences=req.evidences,
        scope=req.scope,
        scope_id=req.scope_id,
    )
    return {"status": "success", "node_id": req.node_id, "health": record.model_dump()}


@router.post("/changes")
def record_change(req: RecordChangeRequest) -> dict[str, Any]:
    change = environment_service.record_change(
        resource_id=req.resource_id,
        change_type=req.change_type,
        before=req.before,
        after=req.after,
        source=req.source,
        scope=req.scope,
        scope_id=req.scope_id,
    )
    return {"status": "success", "change": change.model_dump()}


@router.post("/drifts")
def record_drift(req: RecordDriftRequest) -> dict[str, Any]:
    drift = environment_service.record_drift(
        resource_id=req.resource_id,
        drift_type=req.drift_type,
        expected=req.expected,
        actual=req.actual,
        evidence=req.evidence,
    )
    return {"status": "success", "drift": drift.model_dump()}


@router.post("/snapshots")
def create_snapshot(
    scope: ScopeType = Query(ScopeType.SYSTEM),
    scope_id: str | None = Query(None),
) -> dict[str, Any]:
    snap = environment_service.create_snapshot(scope=scope, scope_id=scope_id)
    return {"status": "success", "snapshot": snap.model_dump()}


@router.get("/as-of")
def get_state_as_of(
    as_of: str = Query(..., description="Target ISO timestamp"),
    scope: ScopeType = Query(ScopeType.SYSTEM),
    scope_id: str | None = Query(None),
) -> dict[str, Any]:
    try:
        snap = environment_service.get_state_as_of(as_of_time=as_of, scope=scope, scope_id=scope_id)
        if not snap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No snapshot available for timestamp.")
        return {"status": "success", "snapshot": snap.model_dump()}
    except FutureLeakageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/incidents")
def create_incident(req: CreateIncidentRequest) -> dict[str, Any]:
    inc = environment_service.create_incident(
        scope=req.scope,
        symptoms=req.symptoms,
        affected_resources=req.affected_resources,
        evidence=req.evidence,
        suspected_cause=req.suspected_cause,
        root_cause=req.root_cause,
        scope_id=req.scope_id,
    )
    return {"status": "success", "incident": inc.model_dump()}


@router.post("/what-if")
def simulate_what_if(req: WhatIfRequest) -> dict[str, Any]:
    res = environment_service.simulate_what_if(
        target_node_id=req.target_node_id,
        event=req.event,
        scope=req.scope,
        scope_id=req.scope_id,
    )
    return {"status": "success", "simulation": res.model_dump()}


@router.post("/remediation/propose")
def propose_remediation(req: ProposeRemediationRequest) -> dict[str, Any]:
    try:
        plan = environment_service.propose_remediation_plan(
            target=req.target,
            current_state=req.current_state,
            desired_state=req.desired_state,
            risk=req.risk,
            dependencies=req.dependencies,
            rollback_target=req.rollback_target,
            rollback_verified=req.rollback_verified,
            is_production=req.is_production,
        )
        return {"status": "success", "plan": plan.model_dump()}
    except UnverifiedRollbackError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/remediation/auto-heal")
def auto_heal(req: AutoHealRequest) -> dict[str, Any]:
    try:
        ok = environment_service.execute_auto_healing(
            resource_id=req.resource_id,
            plan_id=req.plan_id,
            is_pre_authorized=req.is_pre_authorized,
        )
        return {"status": "success", "executed": ok}
    except RemediationLoopError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


@router.get("/summary")
def get_environment_summary(scope: ScopeType = Query(ScopeType.SYSTEM)) -> dict[str, Any]:
    return environment_service.generate_environment_summary(scope=scope)


@router.get("/context")
def get_environment_context(
    query: str = Query(...),
    scope: ScopeType = Query(ScopeType.SYSTEM),
) -> dict[str, Any]:
    return environment_service.get_environment_context(task_query=query, scope=scope)


@router.get("/topology/dependents/{node_id}")
def get_dependents(node_id: str, scope: ScopeType = Query(ScopeType.SYSTEM)) -> dict[str, Any]:
    deps = environment_service.query_dependents(node_id=node_id, scope=scope)
    return {"node_id": node_id, "dependents": deps}


@router.get("/topology/dependencies/{node_id}")
def get_dependencies(node_id: str, scope: ScopeType = Query(ScopeType.SYSTEM)) -> dict[str, Any]:
    deps = environment_service.query_dependencies(node_id=node_id, scope=scope)
    return {"node_id": node_id, "dependencies": deps}


@router.get("/topology/unhealthy")
def get_unhealthy(scope: ScopeType = Query(ScopeType.SYSTEM)) -> dict[str, Any]:
    return {"unhealthy_resources": environment_service.query_unhealthy_resources(scope=scope)}


@router.get("/topology/production")
def get_production() -> dict[str, Any]:
    return {"production_resources": environment_service.query_production_resources()}
