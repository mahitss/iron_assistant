"""FastAPI router exposing Kairo's System State Graph, Self-Model & Diagnostics (Task 93 Phase 28).

Mount path: /api/v1/system-state and /api/system-state
Strictly respects EmergencyStop and read-only non-authoritative invariants.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.exceptions import EmergencyStopActiveError
from app.system_state.models import SelfModelAnswers, SystemDiagnosis
from app.system_state.service import (
    SystemStateService,
    get_system_state_service,
)

router = APIRouter(tags=["System State Graph & Operational Digital Twin (Task 93)"])


def get_service(db: Session = Depends(get_db)) -> SystemStateService:
    return get_system_state_service(db=db)


class SnapshotCreateRequest(BaseModel):
    watermark: int | None = None
    metadata: dict[str, Any] = {}
    user_id: str | None = None


class ReconcileRequest(BaseModel):
    watermark_start: int = 0
    watermark_end: int = 0
    user_id: str | None = None


# ==============================================================================
# 1. System Overview & Health
# ==============================================================================


@router.get("/system-state/summary")
def get_system_summary(service: SystemStateService = Depends(get_service)) -> dict[str, Any]:
    """Retrieve high-level operational overview, component counts, and health status."""
    return service.get_summary()


@router.get("/system-state/health")
def get_system_health(service: SystemStateService = Depends(get_service)) -> dict[str, Any]:
    """Query composite operational health and degraded components."""
    return service.get_health()


@router.get("/system-state/diagnostics", response_model=SystemDiagnosis)
def get_system_diagnostics(service: SystemStateService = Depends(get_service)) -> SystemDiagnosis:
    """Produce structured self-diagnostic report across health, resources, and unverified assumptions."""
    return service.get_diagnostics()


@router.get("/system-state/self-model", response_model=SelfModelAnswers)
def get_self_model_introspections(service: SystemStateService = Depends(get_service)) -> SelfModelAnswers:
    """Answer Kairo's canonical introspective questions ('What am I doing?', 'What is broken?', etc.)."""
    return service.get_self_model_answers()


# ==============================================================================
# 2. Interactive Operational Graph & Topology
# ==============================================================================


@router.get("/system-state/graph")
def get_system_state_graph(service: SystemStateService = Depends(get_service)) -> dict[str, Any]:
    """Return nodes and directed edges formatted for interactive network visualization."""
    return service.get_graph_data()


@router.get("/system-state/resources")
def get_system_resources(service: SystemStateService = Depends(get_service)) -> dict[str, Any]:
    """Query resource pools, active allocations, and pressure points."""
    return service.get_resources()


@router.get("/system-state/dependencies")
def get_system_dependencies(service: SystemStateService = Depends(get_service)) -> dict[str, Any]:
    """Query internal and external operational dependencies."""
    return service.get_dependencies()


@router.get("/system-state/incidents")
def get_system_incidents(service: SystemStateService = Depends(get_service)) -> dict[str, Any]:
    """List active operational incidents and affected downstream components."""
    return service.get_incidents()


# ==============================================================================
# 3. Snapshots & State Deltas
# ==============================================================================


@router.get("/system-state/changes")
def get_state_changes(
    limit: int = Query(default=50, ge=1, le=500),
    service: SystemStateService = Depends(get_service),
) -> list[dict[str, Any]]:
    """Query recent state deltas and cascading impact records."""
    deltas = service.get_recent_deltas(limit=limit)
    return [d.model_dump(mode="json") for d in deltas]


@router.get("/system-state/snapshots")
def list_snapshots(
    limit: int = Query(default=20, ge=1, le=100),
    service: SystemStateService = Depends(get_service),
) -> list[dict[str, Any]]:
    """List historical immutable system state snapshots."""
    return service.list_snapshots(limit=limit)


@router.get("/system-state/snapshots/{snapshot_id}")
def get_snapshot_detail(
    snapshot_id: str,
    service: SystemStateService = Depends(get_service),
) -> dict[str, Any]:
    """Fetch complete immutable snapshot by identifier."""
    snap = service.get_snapshot(snapshot_id)
    if not snap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Snapshot '{snapshot_id}' not found")
    return snap.model_dump(mode="json")


@router.post("/system-state/snapshot", status_code=status.HTTP_201_CREATED)
def create_snapshot_endpoint(
    req: SnapshotCreateRequest,
    service: SystemStateService = Depends(get_service),
) -> dict[str, Any]:
    """Capture a new immutable state snapshot and record differentials."""
    try:
        snap = service.create_snapshot(watermark=req.watermark, metadata=req.metadata, user_id=req.user_id)
        return snap.model_dump(mode="json")
    except EmergencyStopActiveError as err:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(err))


# ==============================================================================
# 4. Targeted Graph & Impact Queries
# ==============================================================================


@router.get("/system-state/impact/{component_id}")
def query_component_impact(
    component_id: str,
    service: SystemStateService = Depends(get_service),
) -> dict[str, Any]:
    """Determine downstream impact if component_id fails or degrades."""
    return service.query_impact(component_id)


@router.get("/system-state/dependents/{component_id}")
def query_component_dependents(
    component_id: str,
    service: SystemStateService = Depends(get_service),
) -> dict[str, Any]:
    """Find all upstream entities that depend on component_id."""
    return service.query_dependents(component_id)


@router.get("/system-state/goals/{goal_id}")
def query_goal_state(
    goal_id: str,
    service: SystemStateService = Depends(get_service),
) -> dict[str, Any]:
    """Query operational state, blockers, resources, and incidents for a specific goal."""
    return service.query_goal(goal_id)


@router.get("/system-state/tasks/{task_id}")
def query_task_state(
    task_id: str,
    service: SystemStateService = Depends(get_service),
) -> dict[str, Any]:
    """Query operational state, serving goals, and dependencies for a specific task."""
    return service.query_task(task_id)


# ==============================================================================
# 5. Startup & On-Demand Reconciliation
# ==============================================================================


@router.post("/system-state/reconcile")
def run_reconciliation(
    req: ReconcileRequest,
    service: SystemStateService = Depends(get_service),
) -> dict[str, Any]:
    """Trigger operational state reconciliation against live subsystems."""
    try:
        return service.reconcile(
            watermark_start=req.watermark_start,
            watermark_end=req.watermark_end,
            user_id=req.user_id,
        )
    except EmergencyStopActiveError as err:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(err))
