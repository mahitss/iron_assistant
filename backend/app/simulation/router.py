"""FastAPI REST API router for Kairo Simulation & Counterfactual Planning Engine (Task 56)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.simulation.calibration import calibrator
from app.simulation.safety import (
    ProductionMutationBlockedError,
    SimulationResourceBudgetExceededError,
    SimulationSideEffectError,
)
from app.simulation.schemas import (
    CalibrationMetric,
    ExecutionGate,
    Scenario,
    ScenarioComparison,
    ScenarioType,
    SimulatedIntervention,
    Simulation,
    SimulationObjective,
    SimulationSnapshot,
)
from app.simulation.service import simulation_service

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


# Request schemas
class CaptureSnapshotRequest(BaseModel):
    source_entity: str = "digital_twin"
    world_state: dict[str, Any] | None = None
    digital_twin_state: dict[str, Any] | None = None
    telemetry_state: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None


class CreateScenarioRequest(BaseModel):
    name: str
    scenario_type: ScenarioType | str = "CUSTOM"
    baseline_snapshot_id: str
    interventions: list[SimulatedIntervention] = Field(default_factory=list)
    objectives: list[SimulationObjective] = Field(default_factory=list)
    horizon: str = "SHORT_TERM"


class RunSimulationRequest(BaseModel):
    scenario_id: str
    creator: str = "kairo_autonomous_supervisor"


class CompareSimulationsRequest(BaseModel):
    simulation_ids: list[str]


class RankSimulationsRequest(BaseModel):
    simulation_ids: list[str]
    user_priorities: dict[str, float] | None = None


class CounterfactualRequest(BaseModel):
    query_type: str = "WHAT_IF_WE_WAIT"  # WHAT_IF_WE_WAIT, WHAT_IF_PLAN_B
    baseline_state: dict[str, Any] = Field(default_factory=dict)
    wait_seconds: int = 300
    plan_b_interventions: list[SimulatedIntervention] = Field(default_factory=list)


class MonteCarloRequest(BaseModel):
    metric_name: str
    base_value: float
    distribution_type: str = "NORMAL"
    std_dev: float = 5.0
    iterations: int = 100
    seed: int = 42


class ReplayRequest(BaseModel):
    snapshot_id: str
    scenario_id: str


class EvaluateGateRequest(BaseModel):
    simulation_id: str
    current_real_state: dict[str, Any] | None = None
    user_approved: bool = False
    user_roles: list[str] = Field(default_factory=list)


class CalibrateRequest(BaseModel):
    simulation_id: str
    metric_name: str
    predicted_value: float
    actual_value: float


# Routes: Snapshots
@router.post("/snapshots", response_model=SimulationSnapshot)
def capture_snapshot(req: CaptureSnapshotRequest) -> SimulationSnapshot:
    try:
        if req.digital_twin_state is None and req.world_state is None:
            return simulation_service.capture_snapshot_from_environment(
                source_entity=req.source_entity,
                provenance=req.provenance,
            )
        return simulation_service.capture_snapshot(
            source_entity=req.source_entity,
            world_state=req.world_state,
            digital_twin_state=req.digital_twin_state,
            telemetry_state=req.telemetry_state,
            provenance=req.provenance,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/snapshots", response_model=list[SimulationSnapshot])
def list_snapshots() -> list[SimulationSnapshot]:
    return simulation_service.list_snapshots()


@router.get("/snapshots/{snapshot_id}", response_model=SimulationSnapshot)
def get_snapshot(snapshot_id: str) -> SimulationSnapshot:
    snap = simulation_service.get_snapshot(snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Snapshot '{snapshot_id}' not found.")
    return snap


# Routes: Scenarios
@router.post("/scenarios", response_model=Scenario)
def create_scenario(req: CreateScenarioRequest) -> Scenario:
    try:
        return simulation_service.create_scenario(
            name=req.name,
            scenario_type=req.scenario_type,
            baseline_snapshot_id=req.baseline_snapshot_id,
            interventions=req.interventions,
            objectives=req.objectives,
            horizon=req.horizon,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scenarios", response_model=list[Scenario])
def list_scenarios(baseline_snapshot_id: str | None = None) -> list[Scenario]:
    return simulation_service.list_scenarios(baseline_snapshot_id)


@router.get("/scenarios/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: str) -> Scenario:
    scen = simulation_service.get_scenario(scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return scen


# Routes: Simulations
@router.post("/run", response_model=Simulation)
def run_simulation(req: RunSimulationRequest) -> Simulation:
    try:
        return simulation_service.run_simulation(
            scenario_id=req.scenario_id,
            creator=req.creator,
        )
    except (SimulationSideEffectError, ProductionMutationBlockedError) as e:
        raise HTTPException(status_code=403, detail=f"FIREWALL BLOCKED: {e}")
    except SimulationResourceBudgetExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs", response_model=list[Simulation])
def list_simulations() -> list[Simulation]:
    return simulation_service.list_simulations()


@router.get("/runs/{simulation_id}", response_model=Simulation)
def get_simulation(simulation_id: str) -> Simulation:
    sim = simulation_service.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found.")
    return sim


# Routes: Comparison & Ranking
@router.post("/compare", response_model=ScenarioComparison)
def compare_simulations(req: CompareSimulationsRequest) -> ScenarioComparison:
    return simulation_service.compare_simulations(req.simulation_ids)


@router.post("/rank")
def rank_simulations(req: RankSimulationsRequest) -> list[dict[str, Any]]:
    explanations = simulation_service.rank_simulations(req.simulation_ids, req.user_priorities)
    return [e.model_dump() for e in explanations]


# Routes: Counterfactuals & Forecasting
@router.post("/counterfactual")
def explore_counterfactual(req: CounterfactualRequest) -> dict[str, Any]:
    if req.query_type == "WHAT_IF_PLAN_B":
        res = simulation_service.explore_counterfactual_plan_b(
            baseline_state=req.baseline_state,
            plan_b_interventions=req.plan_b_interventions,
        )
    else:
        res = simulation_service.explore_counterfactual_what_if_wait(
            baseline_state=req.baseline_state,
            wait_seconds=req.wait_seconds,
        )
    return res.model_dump()


@router.post("/monte-carlo")
def run_monte_carlo(req: MonteCarloRequest) -> dict[str, Any]:
    try:
        res = simulation_service.run_monte_carlo(
            metric_name=req.metric_name,
            base_value=req.base_value,
            distribution_type=req.distribution_type,
            std_dev=req.std_dev,
            iterations=req.iterations,
            seed=req.seed,
        )
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/replay")
def replay_scenario(req: ReplayRequest) -> dict[str, Any]:
    try:
        result, was_cached = simulation_service.replay_scenario(
            snapshot_id=req.snapshot_id,
            scenario_id=req.scenario_id,
        )
        return {"run_result": result.model_dump(), "was_cached": was_cached}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Routes: ExecutionGate & Transition
@router.post("/gates/evaluate", response_model=ExecutionGate)
def evaluate_gate(req: EvaluateGateRequest) -> ExecutionGate:
    try:
        return simulation_service.evaluate_execution_gate(
            simulation_id=req.simulation_id,
            current_real_state=req.current_real_state,
            user_approved=req.user_approved,
            user_roles=req.user_roles,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Routes: Calibration
@router.post("/calibrate", response_model=CalibrationMetric)
def record_calibration(req: CalibrateRequest) -> CalibrationMetric:
    return simulation_service.record_actual_outcome(
        simulation_id=req.simulation_id,
        metric_name=req.metric_name,
        predicted_value=req.predicted_value,
        actual_value=req.actual_value,
    )


@router.get("/calibrations/report")
def get_calibration_report(metric_name: str = Query(..., description="Metric name to report on")) -> dict[str, Any]:
    rep = calibrator.evaluate_model_calibration(metric_name)
    return rep.model_dump()
