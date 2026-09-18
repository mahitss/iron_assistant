"""FastAPI REST router for Kairo Autonomous Temporal Intelligence (Task 111)."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.temporal.domain import (
    ChangeSet,
    StateTransition,
    TemporalAnomaly,
    TemporalCheckpoint,
    TemporalEntity,
    TemporalEvent,
    TemporalGap,
    TemporalQuery,
    TemporalQueryResult,
    TemporalWatermark,
    Timeline,
    utc_now,
)
from app.temporal.schemas import (
    CheckpointCreateRequest,
    DiffRequest,
    HealthCheckResponse,
    ReconstructionRequest,
    StateAtTimeResponse,
    TemporalQueryRequest,
    TimelineResponse,
)
from app.temporal.service import TemporalIntelligenceService

router = APIRouter(prefix="/temporal", tags=["Autonomous Temporal Intelligence"])


def get_service() -> TemporalIntelligenceService:
    return TemporalIntelligenceService.get_instance()


@router.get("/health", response_model=HealthCheckResponse)
def health_check() -> HealthCheckResponse:
    """Returns operational telemetry for Temporal Intelligence engine."""
    svc = get_service()
    return HealthCheckResponse(
        status="HEALTHY",
        subsystem="temporal_intelligence",
        events_count=len(svc._events),
        transitions_count=len(svc._transitions),
        anomalies_count=len(svc._anomalies),
        gaps_count=len(svc._gaps),
        active_watermarks=len(svc._watermarks),
        timestamp=utc_now(),
    )


@router.post("/query", response_model=TemporalQueryResult)
def query_temporal(req: TemporalQueryRequest) -> TemporalQueryResult:
    """Executes a bounded temporal query across events, transitions, gaps, and anomalies."""
    svc = get_service()
    query = TemporalQuery(
        entity_id=req.entity_id,
        from_time=req.from_time,
        to_time=req.to_time,
        scope=req.scope,
        category=req.category,
        limit=req.limit,
        include_events=req.include_events,
        include_transitions=req.include_transitions,
        include_anomalies=req.include_anomalies,
        include_gaps=req.include_gaps,
    )
    return svc.execute_query(query)


@router.get("/timeline/{entity_id}", response_model=TimelineResponse)
def get_entity_timeline(
    entity_id: str,
    from_time: Optional[datetime] = Query(default=None),
    to_time: Optional[datetime] = Query(default=None),
) -> TimelineResponse:
    """Returns a chronologically ordered timeline for a specific entity."""
    svc = get_service()
    tl = svc.get_timeline(entity_id=entity_id, from_time=from_time, to_time=to_time)
    events = [e for seg in tl.segments for e in seg.events]
    transitions = [t for seg in tl.segments for t in seg.transitions]
    return TimelineResponse(
        timeline_id=tl.timeline_id,
        entity_id=entity_id,
        start_time=tl.start_time,
        end_time=tl.end_time,
        total_events=tl.total_events,
        total_transitions=tl.total_transitions,
        events=events,
        transitions=transitions,
    )


@router.get("/state/{entity_id}")
def get_current_state(entity_id: str) -> Dict[str, Any]:
    """Retrieves current active state for an entity."""
    svc = get_service()
    ent = svc._entities.get(entity_id)
    if not ent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entity '{entity_id}' not found")
    return {
        "entity_id": ent.entity_id,
        "entity_type": ent.entity_type.value,
        "scope": ent.scope,
        "current_state": ent.current_state,
        "current_version": ent.current_version,
        "valid_from": ent.valid_from.isoformat(),
        "last_transition_time": ent.last_transition_time.isoformat(),
        "confidence": ent.confidence,
    }


@router.get("/state/{entity_id}/as-of", response_model=StateAtTimeResponse)
def get_state_as_of(
    entity_id: str,
    timestamp: datetime = Query(...),
) -> StateAtTimeResponse:
    """Reconstructs the historical state of an entity at exact time T.
    
    Strict Invariant: The result is explicitly marked with is_historical_reconstruction: true.
    """
    svc = get_service()
    res = svc.state_as_of(entity_id=entity_id, as_of_time=timestamp)
    return StateAtTimeResponse(
        entity_id=entity_id,
        state=res["state"],
        as_of_time=res["as_of_time"],
        effective_from=res.get("effective_from"),
        confidence=res.get("confidence", 1.0),
        is_historical_reconstruction=True,
        source=res.get("source", "system"),
    )


@router.post("/diff")
def compute_semantic_diff(req: DiffRequest) -> Dict[str, Any]:
    """Computes a 'What Changed?' semantic diff between two states."""
    svc = get_service()
    cs = svc.compute_diff(
        state_a=req.state_a,
        state_b=req.state_b,
        from_reference=req.from_reference,
        to_reference=req.to_reference,
        entity_id=req.entity_id,
    )
    return cs.model_dump(mode="json")


@router.get("/changes")
def list_recent_changesets(limit: int = Query(default=20, le=100)) -> List[Dict[str, Any]]:
    """Lists persisted change sets."""
    svc = get_service()
    sets = sorted(svc._changesets.values(), key=lambda c: c.created_at, reverse=True)[:limit]
    return [c.model_dump(mode="json") for c in sets]


@router.get("/gaps", response_model=List[TemporalGap])
def list_temporal_gaps() -> List[TemporalGap]:
    """Lists unobserved telemetry windows / temporal gaps."""
    svc = get_service()
    return svc.list_gaps()


@router.get("/anomalies", response_model=List[TemporalAnomaly])
def list_temporal_anomalies() -> List[TemporalAnomaly]:
    """Lists detected temporal and timing anomalies."""
    svc = get_service()
    return svc.list_anomalies()


@router.get("/watermarks", response_model=List[TemporalWatermark])
def list_watermarks() -> List[TemporalWatermark]:
    """Returns active ingestion and reconciliation watermarks."""
    svc = get_service()
    return svc.list_watermarks()


@router.get("/checkpoints", response_model=List[TemporalCheckpoint])
def list_checkpoints() -> List[TemporalCheckpoint]:
    """Lists captured checkpoints."""
    svc = get_service()
    return svc.list_checkpoints()


@router.post("/checkpoints", status_code=status.HTTP_201_CREATED, response_model=TemporalCheckpoint)
def create_checkpoint(req: CheckpointCreateRequest) -> TemporalCheckpoint:
    """Captures a new stable temporal checkpoint."""
    svc = get_service()
    return svc.create_checkpoint(
        name=req.name,
        checkpoint_type=req.checkpoint_type,
        entity_states=req.entity_states if req.entity_states else None,
        metadata=req.metadata,
    )


@router.post("/reconstruct")
def reconstruct_offline(req: ReconstructionRequest) -> Dict[str, Any]:
    """Reconciles state after an offline disconnection window."""
    svc = get_service()
    cs, gaps = svc.reconcile_offline(
        subsystem=req.subsystem,
        prior_state=req.prior_state,
        observed_current_state=req.observed_state,
        reconnect_time=req.reconnect_time,
    )
    return {
        "status": "RECONCILED",
        "changeset": cs.model_dump(mode="json"),
        "gaps_detected": [g.model_dump(mode="json") for g in gaps],
    }


@router.get("/events/{event_id}")
def get_temporal_event(event_id: str) -> Dict[str, Any]:
    """Retrieves normalized temporal event by canonical or temporal event ID."""
    svc = get_service()
    for e in svc._events.values():
        if e.temporal_event_id == event_id or e.canonical_event_id == event_id:
            return e.model_dump(mode="json")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event '{event_id}' not found")
