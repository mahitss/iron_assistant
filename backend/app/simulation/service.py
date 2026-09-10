"""Unified SimulationService facade orchestrating simulations, scenarios, comparisons, and gates."""

from __future__ import annotations

import logging
from typing import Any

from app.simulation.calibration import calibrator
from app.simulation.comparison import ScenarioComparator, ScenarioDiffSummary
from app.simulation.counterfactuals import CounterfactualEngine, CounterfactualResult
from app.simulation.deterministic import DeterministicRunResult
from app.simulation.engine import SimulationEngine
from app.simulation.execution_gate import transition_engine
from app.simulation.forecasting import FutureStateForecaster, HorizonProjection
from app.simulation.monte_carlo import DistributionParam, MonteCarloEngine, MonteCarloResult
from app.simulation.ranking import PlanExplanation, ScenarioRanker
from app.simulation.replay import SimulationReplayEngine
from app.simulation.scenarios import scenario_manager
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
from app.simulation.snapshots import snapshot_manager
from app.simulation.world import DigitalWorldModelBridge

logger = logging.getLogger("kairo.simulation.service")


class SimulationService:
    """High-level service orchestrator for all simulation and counterfactual planning features."""

    def __init__(self) -> None:
        self._engine = SimulationEngine()
        self._world_bridge = DigitalWorldModelBridge()
        self._comparator = ScenarioComparator()
        self._ranker = ScenarioRanker()
        self._cf_engine = CounterfactualEngine()
        self._forecaster = FutureStateForecaster()
        self._mc_engine = MonteCarloEngine()
        self._replay_engine = SimulationReplayEngine()
        self._simulations: dict[str, Simulation] = {}

    # 1. Snapshots
    def capture_snapshot_from_environment(
        self,
        source_entity: str = "digital_twin",
        provenance: dict[str, Any] | None = None,
    ) -> SimulationSnapshot:
        """Captures a fresh snapshot directly from active Digital Twin / World Model."""
        env_state = self._world_bridge.fetch_verified_environment_state()
        return snapshot_manager.capture_snapshot(
            source_entity=source_entity,
            digital_twin_state=env_state,
            telemetry_state=env_state.get("network_latency", {}),
            provenance=provenance,
        )

    def capture_snapshot(
        self,
        source_entity: str = "custom",
        world_state: dict[str, Any] | None = None,
        digital_twin_state: dict[str, Any] | None = None,
        telemetry_state: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> SimulationSnapshot:
        """Captures a snapshot from explicit state dictionaries."""
        return snapshot_manager.capture_snapshot(
            source_entity=source_entity,
            world_state=world_state,
            digital_twin_state=digital_twin_state,
            telemetry_state=telemetry_state,
            provenance=provenance,
        )

    def get_snapshot(self, snapshot_id: str) -> SimulationSnapshot | None:
        return snapshot_manager.get_snapshot(snapshot_id)

    def list_snapshots(self) -> list[SimulationSnapshot]:
        return snapshot_manager.list_snapshots()

    # 2. Scenarios
    def create_scenario(
        self,
        name: str,
        scenario_type: ScenarioType | str,
        baseline_snapshot_id: str,
        interventions: list[SimulatedIntervention] | None = None,
        objectives: list[SimulationObjective] | None = None,
        horizon: str = "SHORT_TERM",
    ) -> Scenario:
        return scenario_manager.create_scenario(
            name=name,
            scenario_type=scenario_type,
            baseline_snapshot_id=baseline_snapshot_id,
            interventions=interventions,
            objectives=objectives,
            horizon=horizon,
        )

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        return scenario_manager.get_scenario(scenario_id)

    def list_scenarios(self, baseline_snapshot_id: str | None = None) -> list[Scenario]:
        return scenario_manager.list_scenarios(baseline_snapshot_id)

    # 3. Running Simulations
    def run_simulation(
        self,
        scenario_id: str,
        creator: str = "kairo_autonomous_supervisor",
    ) -> Simulation:
        """Executes a sandboxed simulation of the scenario against its baseline snapshot."""
        scen = scenario_manager.get_scenario(scenario_id)
        if scen is None:
            raise KeyError(f"Scenario '{scenario_id}' not found.")

        snap = snapshot_manager.get_snapshot(scen.baseline_snapshot_id)
        if snap is None:
            raise KeyError(f"Baseline snapshot '{scen.baseline_snapshot_id}' not found.")

        sim = self._engine.run_simulation(
            snapshot=snap,
            scenario=scen,
            creator=creator,
        )
        self._simulations[sim.simulation_id] = sim
        return sim

    def get_simulation(self, simulation_id: str) -> Simulation | None:
        return self._simulations.get(simulation_id)

    def list_simulations(self) -> list[Simulation]:
        return list(self._simulations.values())

    # 4. Multi-Scenario Comparison & Ranking
    def compare_simulations(self, simulation_ids: list[str]) -> ScenarioComparison:
        sims = [self._simulations[sid] for sid in simulation_ids if sid in self._simulations]
        return self._comparator.compare_simulations(sims)

    def diff_scenarios(self, sim_a_id: str, sim_b_id: str) -> ScenarioDiffSummary:
        sim_a = self._simulations[sim_a_id]
        sim_b = self._simulations[sim_b_id]
        return self._comparator.diff_scenarios(sim_a, sim_b)

    def rank_simulations(
        self,
        simulation_ids: list[str],
        user_priorities: dict[str, float] | None = None,
    ) -> list[PlanExplanation]:
        sims = [self._simulations[sid] for sid in simulation_ids if sid in self._simulations]
        return self._ranker.rank_scenarios(sims, user_priorities)

    # 5. Counterfactual Queries
    def explore_counterfactual_what_if_wait(
        self,
        baseline_state: dict[str, Any],
        wait_seconds: int = 300,
    ) -> CounterfactualResult:
        return self._cf_engine.what_if_we_wait(baseline_state, wait_seconds)

    def explore_counterfactual_plan_b(
        self,
        baseline_state: dict[str, Any],
        plan_b_interventions: list[SimulatedIntervention],
    ) -> CounterfactualResult:
        return self._cf_engine.what_if_plan_b(baseline_state, plan_b_interventions)

    # 6. Forecasting & Monte Carlo
    def forecast_trajectory(
        self,
        baseline_state: dict[str, Any],
        traffic_growth_rate: float = 0.05,
    ) -> list[HorizonProjection]:
        return self._forecaster.forecast_trajectory(baseline_state, 0, traffic_growth_rate)

    def run_monte_carlo(
        self,
        metric_name: str,
        base_value: float,
        distribution_type: str = "NORMAL",
        std_dev: float = 5.0,
        iterations: int = 100,
        seed: int = 42,
    ) -> MonteCarloResult:
        param = DistributionParam(
            distribution_type=distribution_type,
            mean=0.0,
            std_dev=std_dev,
        )
        return self._mc_engine.run_simulation(
            metric_name=metric_name,
            base_value=base_value,
            distribution=param,
            iterations=iterations,
            seed=seed,
        )

    # 7. Replay
    def replay_scenario(self, snapshot_id: str, scenario_id: str) -> tuple[DeterministicRunResult, bool]:
        snap = snapshot_manager.get_snapshot(snapshot_id)
        scen = scenario_manager.get_scenario(scenario_id)
        if snap is None or scen is None:
            raise KeyError("Snapshot or scenario not found for replay.")
        return self._replay_engine.replay_scenario(snap, scen)

    # 8. ExecutionGate & Real-World Transition
    def evaluate_execution_gate(
        self,
        simulation_id: str,
        current_real_state: dict[str, Any] | None = None,
        user_approved: bool = False,
        user_roles: list[str] | None = None,
    ) -> ExecutionGate:
        sim = self._simulations.get(simulation_id)
        if sim is None:
            raise KeyError(f"Simulation '{simulation_id}' not found.")
        snap = snapshot_manager.get_snapshot(sim.source_snapshot_id)
        if snap is None:
            raise KeyError(f"Snapshot '{sim.source_snapshot_id}' not found.")

        real_state = current_real_state or self._world_bridge.fetch_verified_environment_state()
        return transition_engine.evaluate_gate(
            simulation=sim,
            snapshot=snap,
            current_real_state=real_state,
            user_approved=user_approved,
            user_roles=user_roles,
        )

    # 9. Calibration
    def record_actual_outcome(
        self,
        simulation_id: str,
        metric_name: str,
        predicted_value: float,
        actual_value: float,
    ) -> CalibrationMetric:
        return calibrator.record_outcome_pair(
            simulation_id=simulation_id,
            metric_name=metric_name,
            predicted=predicted_value,
            actual_observed=actual_value,
        )


# Global singleton service
simulation_service = SimulationService()
