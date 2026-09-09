"""FastAPI REST API router for Kairo Resilience, Circuit Breakers, and System Reliability."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.resilience.manager import resilience_manager
from app.resilience.schemas import (
    CircuitBreakerStatus,
    QuarantineRecord,
    RecoveryState,
    SystemReliabilityDashboard,
)

router = APIRouter(prefix="/resilience", tags=["Resilience & Fault-Tolerance"])


@router.get("/health", summary="Get system liveness, readiness, and dependency health")
async def get_health(session: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    """Probes critical dependencies and returns comprehensive health status."""
    # Probe real database and redis
    await resilience_manager.health_tracker.probe_database(session)
    await resilience_manager.health_tracker.probe_redis()

    is_alive, live_msg = resilience_manager.health_tracker.evaluate_liveness()
    is_ready, ready_msg = resilience_manager.health_tracker.evaluate_readiness()

    return {
        "liveness": {"alive": is_alive, "message": live_msg},
        "readiness": {"ready": is_ready, "message": ready_msg},
        "read_only_mode": resilience_manager.degradation_mgr.is_read_only_mode,
        "dependencies": [
            r.model_dump() for r in resilience_manager.health_tracker.get_all_reports()
        ],
    }


@router.get("/dashboard", response_model=SystemReliabilityDashboard, summary="System Reliability Dashboard metrics")
async def get_dashboard(session: AsyncSession = Depends(get_db_session)) -> SystemReliabilityDashboard:
    """Returns reliability metrics, circuit breaker states, and active quarantine counts."""
    # Refresh DB probe
    await resilience_manager.health_tracker.probe_database(session)
    return resilience_manager.get_reliability_dashboard()


@router.get("/circuits", response_model=list[CircuitBreakerStatus], summary="List all scoped circuit breakers")
async def list_circuits() -> list[CircuitBreakerStatus]:
    return resilience_manager.circuit_registry.list_all()


@router.post("/circuits/{circuit_id:path}/reset", summary="Reset a circuit breaker to CLOSED")
async def reset_circuit(circuit_id: str) -> dict[str, Any]:
    success = resilience_manager.circuit_registry.reset(circuit_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{circuit_id}' not found",
        )
    return {"status": "ok", "circuit_id": circuit_id, "state": "CLOSED"}


@router.get("/quarantine", response_model=list[QuarantineRecord], summary="List quarantined poison tasks")
async def list_quarantined(session: AsyncSession = Depends(get_db_session)) -> list[QuarantineRecord]:
    return await resilience_manager.quarantine_mgr.list_quarantined(session)


@router.post("/quarantine/{task_id}/release", summary="Operator release of a quarantined task")
async def release_quarantined_task(
    task_id: str,
    released_by: str = Query(default="operator"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    success = await resilience_manager.quarantine_mgr.release_task(
        task_id=task_id,
        released_by=released_by,
        session=session,
    )
    return {"status": "ok", "task_id": task_id, "released": success}


@router.post("/tasks/{task_id}/recover", summary="Evaluate and recover a task with No Blind Resume checks")
async def recover_task(
    task_id: str,
    worker_id: str = Query(default="worker-manual"),
    current_policy_version: int = Query(default=1),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    recovery_state, checkpoint = await resilience_manager.recovery_mgr.evaluate_and_recover(
        task_id=task_id,
        worker_id=worker_id,
        current_policy_version=current_policy_version,
        session=session,
    )
    return {
        "status": "ok",
        "task_id": task_id,
        "recovery_state": recovery_state,
        "checkpoint": checkpoint.model_dump() if checkpoint else None,
    }


@router.post("/degradation/read-only", summary="Toggle read-only degraded mode")
async def set_read_only_mode(enabled: bool = Query(...)) -> dict[str, Any]:
    resilience_manager.degradation_mgr.set_read_only_mode(enabled)
    return {"status": "ok", "read_only_mode": enabled}
