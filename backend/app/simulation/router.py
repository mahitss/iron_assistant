"""REST API Router for Task 89 Autonomous Recovery Simulation & Digital Twin.

Exposes endpoints for:
- Operational Snapshot Capture & Inspection
- Pre-Recovery Consequence Simulation & Pareto Ranking
- Stale Simulation Drift Detection
- Chaos Resiliency Drills (14 canonical scenarios)
- Prediction vs Reality Metacognitive Calibration
- Strategy Scorecards & Multi-dimensional Resilience Benchmarks
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.simulation.recovery_models import (
    ConsistencyLevel,
    PredictionVsRealityRecord,
    RecoveryCandidate,
    RecoverySimulationResult,
    RecoveryStrategyScorecard,
    ResilienceBenchmark,
    SimulationMode,
)
from app.simulation.recovery_service import get_recovery_service

logger = logging.getLogger("kairo.simulation.router")

router = APIRouter(prefix="/api/v1/simulation", tags=["Autonomous Recovery Simulation"])


class SnapshotCaptureRequest(BaseModel):
    custom_overrides: dict[str, Any] | None = None
    consistency: ConsistencyLevel = ConsistencyLevel.BOUNDED


class RunSimulationRequest(BaseModel):
    target_subsystem: str
    hypothesis: str = "Simulate candidate recovery strategies to evaluate optimal Pareto trade-off"
    description: str = "Pre-recovery consequence simulation"
    snapshot_id: str | None = None
    candidate_strategies: list[str] | None = None
    simulation_mode: SimulationMode = SimulationMode.ANALYTICAL


class RunChaosRequest(BaseModel):
    scenario_id: str


class CalibrateRecoveryRequest(BaseModel):
    simulation_id: str
    recovery_id: str
    strategy: str
    actual_duration_seconds: float
    actual_resource_cost: dict[str, Any] = Field(default_factory=dict)
    actual_risk_score: float = 0.1
    actual_blast_radius: float = 0.2
    verification_passed: bool = True


@router.post("/snapshots", summary="Capture immutable operational digital twin snapshot")
async def capture_snapshot(payload: SnapshotCaptureRequest) -> dict[str, Any]:
    svc = get_recovery_service()
    snapshot = await svc.capture_snapshot(
        custom_overrides=payload.custom_overrides,
        consistency=payload.consistency,
    )
    return snapshot.model_dump()


@router.get("/snapshots/latest", summary="Retrieve most recent operational snapshot")
async def get_latest_snapshot() -> dict[str, Any]:
    svc = get_recovery_service()
    snap = svc.twin.get_latest_snapshot()
    if not snap:
        snap = await svc.capture_snapshot()
    return snap.model_dump()


@router.get("/snapshots/{snapshot_id}", summary="Retrieve operational snapshot by ID")
async def get_snapshot_by_id(snapshot_id: str) -> dict[str, Any]:
    svc = get_recovery_service()
    snap = svc.get_snapshot(snapshot_id)
    if not snap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Snapshot '{snapshot_id}' not found")
    return snap.model_dump()


@router.post("/run", summary="Run pre-recovery consequence simulation across candidate strategies")
async def run_simulation(payload: RunSimulationRequest) -> dict[str, Any]:
    svc = get_recovery_service()
    result = await svc.run_simulation(
        target_subsystem=payload.target_subsystem,
        hypothesis=payload.hypothesis,
        description=payload.description,
        snapshot_id=payload.snapshot_id,
        candidate_strategies=payload.candidate_strategies,
        simulation_mode=payload.simulation_mode,
    )
    return result.model_dump()


@router.get("/runs", summary="List historical recovery simulations")
async def list_simulations(limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    svc = get_recovery_service()
    runs = svc.list_simulations(limit=limit)
    return [r.model_dump() for r in runs]


@router.get("/runs/{simulation_id}", summary="Retrieve recovery simulation result by ID")
async def get_simulation_by_id(simulation_id: str) -> dict[str, Any]:
    svc = get_recovery_service()
    res = svc.get_simulation(simulation_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Simulation '{simulation_id}' not found")
    return res.model_dump()


@router.get("/chaos/scenarios", summary="List catalog of 14 canonical chaos drill scenarios")
async def list_chaos_scenarios() -> list[dict[str, Any]]:
    svc = get_recovery_service()
    return svc.list_chaos_scenarios()


@router.post("/chaos/run", summary="Execute an isolated chaos drill in digital twin simulation mode")
async def run_chaos_drill(payload: RunChaosRequest) -> dict[str, Any]:
    svc = get_recovery_service()
    try:
        result = await svc.run_chaos_drill(payload.scenario_id)
        return result.model_dump()
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post("/calibrate", summary="Calibrate simulation predictions against empirical post-recovery reality")
async def calibrate_recovery(payload: CalibrateRecoveryRequest) -> dict[str, Any]:
    svc = get_recovery_service()
    record = svc.record_actual_recovery(
        simulation_id=payload.simulation_id,
        recovery_id=payload.recovery_id,
        strategy=payload.strategy,
        actual_duration_seconds=payload.actual_duration_seconds,
        actual_resource_cost=payload.actual_resource_cost,
        actual_risk_score=payload.actual_risk_score,
        actual_blast_radius=payload.actual_blast_radius,
        verification_passed=payload.verification_passed,
    )
    return record.model_dump()


@router.get("/scorecards", summary="Retrieve historical recovery strategy scorecards")
async def get_scorecards() -> list[dict[str, Any]]:
    svc = get_recovery_service()
    cards = svc.get_scorecards()
    return [c.model_dump() for c in cards]


@router.get("/benchmarks", summary="Retrieve system-level resilience benchmarks (MTTR, MTBF, radar dimensions)")
async def get_benchmarks() -> dict[str, Any]:
    svc = get_recovery_service()
    bmk = svc.get_resilience_benchmark()
    return bmk.model_dump()


@router.get("/regressions", summary="Detect recovery strategies exhibiting performance degradation")
async def get_regressions() -> list[dict[str, Any]]:
    svc = get_recovery_service()
    return svc.get_regressions()


@router.get("/comparisons", summary="Retrieve prediction vs reality calibration history")
async def get_comparisons(limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    svc = get_recovery_service()
    records = svc.get_comparisons(limit=limit)
    return [r.model_dump() for r in records]
