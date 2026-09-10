"""FastAPI REST API router for Continuous Self-Optimization & Adaptive Control Engine (Task 62)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.optimization.safety import (
    ImmutableControlViolationError,
    KillSwitchActiveError,
    OptimizationSafetyError,
)
from app.optimization.schemas import (
    ApproveRecommendationRequest,
    CalibrationRecord,
    CanaryDeployment,
    CanaryDeployRequest,
    ChangeSet,
    CreateExperimentRequest,
    DriftRecord,
    EvaluateOptimizationRequest,
    Experiment,
    ExperimentStatus,
    IngestMeasurementRequest,
    KillSwitchRequest,
    MetricMeasurement,
    OptimizationBaseline,
    OptimizationEvaluation,
    OptimizationRecommendation,
    RollbackPlan,
)
from app.optimization.service import optimization_service

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])


@router.get("/health")
async def optimization_health() -> dict[str, str]:
    """Health check endpoint for optimization subsystem."""
    return {"status": "ok", "subsystem": "optimization"}


@router.post("/evaluate", response_model=OptimizationEvaluation)
async def evaluate_system(req: EvaluateOptimizationRequest) -> OptimizationEvaluation:
    """Run an optimization evaluation cycle across tracked metrics and generate bounded recommendations."""
    try:
        return await optimization_service.evaluate_system(req)
    except (OptimizationSafetyError, KillSwitchActiveError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recommendations", response_model=list[OptimizationRecommendation])
async def list_recommendations() -> list[OptimizationRecommendation]:
    """List active optimization recommendations."""
    return await optimization_service.list_recommendations()


@router.get("/recommendations/{recommendation_id}", response_model=OptimizationRecommendation)
async def get_recommendation(recommendation_id: str) -> OptimizationRecommendation:
    """Retrieve specific recommendation by ID."""
    rec = await optimization_service.get_recommendation(recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{recommendation_id}' not found.")
    return rec


@router.post("/recommendations/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: str,
    req: ApproveRecommendationRequest,
) -> dict[str, Any]:
    """Approve candidate recommendation, instantiate change set, and initiate canary."""
    try:
        req.recommendation_id = recommendation_id
        cs, canary = await optimization_service.approve_recommendation(req)
        return {"change_set": cs.model_dump(), "canary": canary.model_dump()}
    except (OptimizationSafetyError, ImmutableControlViolationError, KillSwitchActiveError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/experiments", response_model=list[Experiment])
async def list_experiments(status: ExperimentStatus | None = None) -> list[Experiment]:
    """List active or historical A/B experiments."""
    return await optimization_service.list_experiments(status=status)


@router.post("/experiments", response_model=Experiment)
async def create_experiment(req: CreateExperimentRequest) -> Experiment:
    """Create a new sandboxed controlled experiment."""
    try:
        return await optimization_service.create_experiment(req)
    except (OptimizationSafetyError, KillSwitchActiveError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}", response_model=Experiment)
async def get_experiment(experiment_id: str) -> Experiment:
    """Retrieve experiment by ID."""
    exp = await optimization_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return exp


@router.post("/experiments/{experiment_id}/approve", response_model=Experiment)
async def approve_experiment(experiment_id: str, approver: str = "ADMIN") -> Experiment:
    """Approve experiment for activation."""
    try:
        return await optimization_service.approve_experiment(experiment_id, approver=approver)
    except (OptimizationSafetyError, KillSwitchActiveError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/experiments/{experiment_id}/start", response_model=Experiment)
async def start_experiment(experiment_id: str) -> Experiment:
    """Activate experiment into RUNNING state."""
    try:
        return await optimization_service.start_experiment(experiment_id)
    except (OptimizationSafetyError, KillSwitchActiveError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/canary/deploy")
async def deploy_canary(req: CanaryDeployRequest) -> dict[str, Any]:
    """Deploy canary partition for change set."""
    try:
        # Fetch change set and initiate canary
        cs = optimization_service._engine.change_set_manager.get_change_set(req.change_set_id)
        if not cs:
            raise HTTPException(status_code=404, detail=f"Change set '{req.change_set_id}' not found.")
        canary = optimization_service._engine.canary_controller.initiate_canary(
            cs, initial_traffic_pct=req.traffic_percentage
        )
        return canary.model_dump()
    except (OptimizationSafetyError, KillSwitchActiveError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/canary/{canary_id}/verify", response_model=CanaryDeployment)
async def verify_canary(
    canary_id: str,
    is_verified: bool = True,
    advance_to_full: bool = True,
) -> CanaryDeployment:
    """Verify canary operation and advance rollout."""
    try:
        return await optimization_service.verify_canary(
            canary_id=canary_id,
            is_verified=is_verified,
            advance_to_full=advance_to_full,
        )
    except (OptimizationSafetyError, KillSwitchActiveError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/canary/{canary_id}/rollback", response_model=RollbackPlan)
async def rollback_canary(
    canary_id: str,
    reason: str = "Rollback requested",
    actor: str = "OPERATOR",
) -> RollbackPlan:
    """Abort canary and verify parameter restoration."""
    try:
        return await optimization_service.rollback_canary(
            canary_id=canary_id,
            reason=reason,
            actor=actor,
        )
    except OptimizationSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/change-sets", response_model=list[ChangeSet])
async def list_change_sets() -> list[ChangeSet]:
    """List tracked change sets."""
    return await optimization_service.list_change_sets()


@router.post("/metrics/measurements", response_model=MetricMeasurement)
async def ingest_measurement(req: IngestMeasurementRequest) -> MetricMeasurement:
    """Ingest raw metric measurement."""
    return await optimization_service.ingest_measurement(req)


@router.get("/metrics")
async def get_metrics_summary() -> list[dict[str, Any]]:
    """Retrieve statistical summary for all tracked metrics."""
    return [a.model_dump() for a in optimization_service._engine.metrics_engine.aggregate_all()]


@router.get("/baselines", response_model=list[OptimizationBaseline])
async def list_baselines() -> list[OptimizationBaseline]:
    """List active metric reference baselines."""
    return await optimization_service.list_baselines()


@router.get("/drift", response_model=list[DriftRecord])
async def list_drift() -> list[DriftRecord]:
    """Retrieve detected drift alerts."""
    return await optimization_service.list_drift()


@router.get("/calibration", response_model=list[CalibrationRecord])
async def list_calibration() -> list[CalibrationRecord]:
    """Retrieve prediction calibration history."""
    return await optimization_service.list_calibration()


@router.get("/audit/trail")
async def get_audit_trail(
    change_set_id: str | None = None,
    experiment_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Retrieve immutable cryptographic audit trail events."""
    return optimization_service.get_audit_trail(
        change_set_id=change_set_id,
        experiment_id=experiment_id,
        limit=limit,
    )


@router.post("/kill-switch")
async def toggle_kill_switch(req: KillSwitchRequest) -> dict[str, Any]:
    """Engage or disengage emergency optimization freeze."""
    return optimization_service.set_kill_switch(
        engage=req.engage,
        reason=req.reason,
        actor=req.actor,
    )
