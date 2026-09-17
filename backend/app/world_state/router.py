"""FastAPI Router for KAIRO World-State Reconstruction, State Estimation, Reality Synchronization & Drift Engine (Task 98, Phase 41)."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.world_state.domain import (
    AnalyzeDriftRequest,
    DeclareExpectedStateRequest,
    ExpectedState,
    HistoricalReconstructionRequest,
    IngestObservationRequest,
    ReconcileStateRequest,
    RevalidationCandidate,
    StateConflictRecord,
    StateDriftRecord,
    StateInvariantViolation,
    StateObservation,
    WorldScope,
    WorldStateDiff,
    WorldStateEntity,
    WorldStateSnapshot,
    utc_now,
)
from app.world_state.reconciliation_engine import (
    WorldStateReconciliationEngine,
    get_world_state_reconciliation_engine,
)

router = APIRouter(tags=["World State & Drift Engine"])


# =====================================================================
# STATE QUERY ENDPOINTS
# =====================================================================

@router.get("/state/current", response_model=Dict[str, Any])
def get_current_world_state(
    scope: Optional[WorldScope] = Query(None),
    user_id: str = Query("default_user"),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Returns the current reconstructed world state, filtered by scope if requested."""
    entities = list(engine._entities.values())
    if scope:
        entities = [e for e in entities if e.scope == scope]

    return {
        "timestamp": utc_now().isoformat(),
        "total_entities": len(entities),
        "entities": [e.model_dump(mode="json") for e in entities],
        "active_conflicts_count": len(engine._conflicts),
        "active_drift_count": len(engine._drift_engine._drift_records),
    }


@router.get("/state/{scope}", response_model=Dict[str, Any])
def get_state_by_scope(
    scope: WorldScope,
    user_id: str = Query("default_user"),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Returns all state entities within a specific operational scope."""
    entities = [e for e in engine._entities.values() if e.scope == scope]
    return {
        "scope": scope.value,
        "count": len(entities),
        "entities": [e.model_dump(mode="json") for e in entities],
    }


@router.get("/state/{scope}/history", response_model=Dict[str, Any])
def get_state_history(
    scope: WorldScope,
    entity_id: Optional[str] = Query(None),
    user_id: str = Query("default_user"),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Returns the versioned mutation history of entities in the given scope."""
    if entity_id:
        canonical_id = engine.resolve_canonical_id(entity_id)
        history = engine._entity_history.get(canonical_id, [])
        return {"entity_id": canonical_id, "history": history}

    # All entities in scope
    scoped_history: dict[str, list[dict[str, Any]]] = {}
    for eid, ent in engine._entities.items():
        if ent.scope == scope:
            scoped_history[eid] = engine._entity_history.get(eid, [])
    return {"scope": scope.value, "history": scoped_history}


@router.get("/state/{scope}/observations", response_model=List[StateObservation])
def get_state_observations(
    scope: WorldScope,
    entity_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> list[StateObservation]:
    """Retrieves ingested observations for an operational scope."""
    obs = engine._observations
    if scope != WorldScope.SYSTEM:
        obs = [o for o in obs if o.scope == scope]
    if entity_id:
        canonical_id = engine.resolve_canonical_id(entity_id)
        obs = [o for o in obs if o.entity_id == canonical_id]
    return obs[-limit:]


@router.get("/state/{scope}/changes", response_model=Dict[str, Any])
def get_state_changes(
    scope: WorldScope,
    since: Optional[datetime] = Query(None),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Returns detected attribute mutations since the specified timestamp."""
    changes = []
    cutoff = since or (utc_now() - timedelta(hours=24))
    for eid, ent in engine._entities.items():
        if scope == WorldScope.SYSTEM or ent.scope == scope:
            for ak, attr in ent.attributes.items():
                if attr.observed_at >= cutoff and attr.previous_value is not None:
                    changes.append({
                        "entity_id": eid,
                        "attribute": ak,
                        "from": attr.previous_value,
                        "to": attr.current_value,
                        "observed_at": attr.observed_at.isoformat(),
                        "source": attr.source,
                    })
    return {"scope": scope.value, "since": cutoff.isoformat(), "changes_count": len(changes), "changes": changes}


@router.get("/state/{scope}/drift", response_model=List[StateDriftRecord])
def get_scope_drift(
    scope: WorldScope,
    status_filter: Optional[str] = Query(None),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> list[StateDriftRecord]:
    """Returns active or historic drift records detected within the specified scope."""
    records = list(engine._drift_engine._drift_records.values())
    if scope != WorldScope.SYSTEM:
        records = [r for r in records if r.scope == scope]
    if status_filter:
        records = [r for r in records if r.status.value == status_filter.upper()]
    return records


@router.get("/state/{scope}/conflicts", response_model=List[StateConflictRecord])
def get_scope_conflicts(
    scope: WorldScope,
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> list[StateConflictRecord]:
    """Returns dialectic conflicts between observation sources within the scope."""
    return list(engine._conflicts.values())


@router.get("/state/{scope}/lineage", response_model=Dict[str, Any])
def get_state_lineage(
    scope: WorldScope,
    entity_id: str = Query(...),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Returns the operational lineage and provenance trail for an entity."""
    canonical_id = engine.resolve_canonical_id(entity_id)
    entity = engine._entities.get(canonical_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entity '{entity_id}' not found.")

    return {
        "entity_id": canonical_id,
        "canonical_name": entity.canonical_name,
        "version": entity.version,
        "provenance": entity.provenance,
        "history": engine._entity_history.get(canonical_id, []),
        "active_drift_ids": entity.active_drift_ids,
        "active_conflict_ids": entity.active_conflict_ids,
    }


# =====================================================================
# STATE ACTION / RECONCILIATION ENDPOINTS
# =====================================================================

@router.post("/state/observe", response_model=StateObservation)
async def ingest_state_observation(
    req: IngestObservationRequest,
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> StateObservation:
    """Ingests a new empirical observation from telemetry, probes, or agent reports."""
    obs = StateObservation(
        source=req.source,
        source_id=req.source_id,
        entity_id=req.entity_id,
        observed_value=req.observed_value,
        observed_at=req.observed_at or utc_now(),
        confidence=req.confidence,
        certainty=req.certainty,
        sensitivity=req.sensitivity,
        scope=req.scope,
        correlation_id=req.correlation_id,
        provenance=req.provenance,
    )
    await engine.ingest_observation(obs)
    return obs


@router.post("/state/expect", response_model=ExpectedState)
def declare_expected_state(
    req: DeclareExpectedStateRequest,
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> ExpectedState:
    """Declares an explicit expected postcondition or contractual constraint."""
    return engine.declare_expected_state(
        entity_id_or_expected=req.entity_id,
        expected_value=req.expected_value,
        expected_by=req.expected_by,
        source_type=req.source_type,
        source_id=req.source_id,
        tolerance=req.tolerance,
        valid_from=req.valid_from,
        valid_until=req.valid_until,
        scope=req.scope,
        metadata=req.metadata,
    )


@router.post("/state/reconcile", response_model=Dict[str, Any])
async def reconcile_state(
    req: ReconcileStateRequest,
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Reconciles expectations against actual state, computing drift and revalidations."""
    results = await engine.reconcile_expectations()
    return {
        "status": "COMPLETED",
        "reconciled_count": len(results),
        "results": {r[0].entity_id: r[1].value for r in results},
    }


@router.post("/state/validate", response_model=List[StateInvariantViolation])
def validate_invariants(
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> list[StateInvariantViolation]:
    """Executes state invariant rules and freshness audits across all entities."""
    return engine.audit_freshness_and_invariants()


@router.post("/state/snapshot", response_model=WorldStateSnapshot)
def create_state_snapshot(
    scope: WorldScope = Query(WorldScope.SYSTEM),
    label: Optional[str] = Query(None),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> WorldStateSnapshot:
    """Captures an immutable, versioned reference snapshot of the current state."""
    return engine.create_snapshot(scope=scope, label=label)


class DiffRequest(BaseModel):
    snapshot_a_id: str
    snapshot_b_id: str


@router.post("/state/diff", response_model=WorldStateDiff)
def compute_state_diff(
    req: DiffRequest,
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> WorldStateDiff:
    """Computes structural differential (ADDED, REMOVED, CHANGED) between two snapshots."""
    return engine.compute_diff(req.snapshot_a_id, req.snapshot_b_id)


@router.post("/state/reconstruct", response_model=Dict[str, Any])
def reconstruct_historical_state(
    req: HistoricalReconstructionRequest,
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Reconstructs the best-supported world state at a historical point in time T."""
    return engine.reconstruct_historical_state(timestamp=req.timestamp, scope=req.scope)


# =====================================================================
# DRIFT API ENDPOINTS
# =====================================================================

@router.post("/drift/analyze", response_model=Dict[str, Any])
def analyze_drift(
    req: AnalyzeDriftRequest,
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> dict[str, Any]:
    """Analyzes drift within the requested scope and returns detected discrepancies."""
    results = engine.reconcile_expectations(entity_id=req.entity_id)
    drift_list = [
        d.model_dump(mode="json")
        for d in engine._drift_engine._drift_records.values()
        if req.scope == WorldScope.SYSTEM or d.scope == req.scope
    ]
    return {
        "scope": req.scope.value,
        "analyzed_outcomes": {k: v.value for k, v in results.items()},
        "active_drift_count": len(drift_list),
        "drift_records": drift_list,
    }


@router.post("/drift/{id}/revalidate", response_model=RevalidationCandidate)
def revalidate_drift(
    id: str,
    priority: str = Query("HIGH"),
    engine: WorldStateReconciliationEngine = Depends(get_world_state_reconciliation_engine),
) -> RevalidationCandidate:
    """Schedules an explicit revalidation candidate for an identified drift record."""
    drift = engine._drift_engine._drift_records.get(id)
    if not drift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drift record '{id}' not found.")

    return engine.schedule_revalidation(
        entity_id=drift.entity_id,
        target_type="STATE_DRIFT",
        reason=f"Manual revalidation triggered for drift '{id}'",
        drift_id=id,
        priority=priority,
    )
