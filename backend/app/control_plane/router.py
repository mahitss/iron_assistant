"""FastAPI REST router for Kairo Autonomous Cognitive Control Plane (Task 102).

Exposes safe query and coordination endpoints.
No endpoint allows direct, unrestricted tool or shell execution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.domain import ControlCycle, ControlMode
from app.control_plane.service import ControlPlaneService, get_control_plane_service
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/control", tags=["control-plane"])


def get_service(
    session: Optional[AsyncSession] = Depends(get_db),
) -> ControlPlaneService:
    return get_control_plane_service(db_session=session)


@router.get("/status")
async def get_control_status(
    service: ControlPlaneService = Depends(get_service),
) -> Dict[str, Any]:
    """Returns high-level control plane health, active mode, and execution metrics."""
    return service.get_status()


@router.get("/mode")
async def get_control_mode(
    service: ControlPlaneService = Depends(get_service),
) -> Dict[str, str]:
    """Returns the current derived supervisory autonomy mode."""
    return {"control_mode": service.get_status()["control_mode"]}


@router.get("/health")
async def get_control_health(
    service: ControlPlaneService = Depends(get_service),
) -> Dict[str, Any]:
    """Returns circuit breaker and queue operational health."""
    stat = service.get_status()
    return {
        "status": "HEALTHY" if not stat["metrics"]["circuit_breaker_tripped"] else "CIRCUIT_BREAKER_TRIPPED",
        "emergency_stop_active": stat["emergency_stop_active"],
        "queue_depth": stat["queue_depth"],
        "metrics": stat["metrics"],
    }


@router.get("/cycles", response_model=List[ControlCycle])
async def list_control_cycles(
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    trigger_type: Optional[str] = None,
    service: ControlPlaneService = Depends(get_service),
) -> List[ControlCycle]:
    """Lists recent control cycles with optional status or trigger filters."""
    return service.list_cycles(limit=limit, status=status, trigger_type=trigger_type)


@router.get("/cycles/{cycle_id}", response_model=ControlCycle)
async def get_control_cycle(
    cycle_id: str,
    service: ControlPlaneService = Depends(get_service),
) -> ControlCycle:
    """Retrieves full metadata and execution trace for a single cycle."""
    cycle = service.get_cycle(cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail=f"ControlCycle '{cycle_id}' not found")
    return cycle


@router.get("/cycles/{cycle_id}/timeline")
async def get_cycle_timeline(
    cycle_id: str,
    service: ControlPlaneService = Depends(get_service),
) -> List[Dict[str, Any]]:
    """Returns chronological stage transitions executed during the cycle."""
    timeline = service.get_cycle_timeline(cycle_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Timeline for cycle '{cycle_id}' not found")
    return timeline


@router.get("/cycles/{cycle_id}/replay")
async def replay_control_cycle(
    cycle_id: str,
    service: ControlPlaneService = Depends(get_service),
) -> Dict[str, Any]:
    """Reconstructs cycle state without executing side-effects (read-only replay)."""
    return service.replay_cycle(cycle_id)


@router.post("/reassess", response_model=ControlCycle)
async def trigger_reassessment(
    scope: str = Query("SYSTEM"),
    service: ControlPlaneService = Depends(get_service),
) -> ControlCycle:
    """Forces an immediate supervisory reassessment pass across all intelligence systems."""
    return service.reassess(scope=scope)
