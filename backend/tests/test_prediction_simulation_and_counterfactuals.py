import pytest
from app.prediction.simulation import (
    ScenarioSimulator,
    SimulationResult,
)
from app.prediction.counterfactual import (
    CounterfactualEngine,
    CounterfactualResult,
)


def test_scenario_simulator_strictly_simulated():
    simulator = ScenarioSimulator()

    result = simulator.simulate_scenario(
        scenario_name="traffic_spike_10x",
        initial_state={"cpu": 40, "memory": 50, "instances": 2},
        steps=3,
        interventions=[{"step": 1, "action": "add_instance", "count": 2}],
    )

    assert isinstance(result, SimulationResult)
    assert result.is_simulated is True
    assert result.label == "SIMULATED"
    # Verify simulation cannot be confused with live telemetry
    for step in result.trajectory:
        assert step.get("source") == "SIMULATION_ENGINE"
        assert step.get("is_authoritative") is False


def test_counterfactual_engine_strictly_hypothetical():
    engine = CounterfactualEngine()

    cf_no_action = engine.evaluate_counterfactual(
        subject="cluster:k8s",
        current_trend="disk_filling_fast",
        proposed_action=None,  # "What if we don't intervene?"
        horizon_hours=24,
    )
    assert isinstance(cf_no_action, CounterfactualResult)
    assert cf_no_action.is_hypothetical is True
    assert cf_no_action.label == "HYPOTHETICAL"
    assert "no intervention" in cf_no_action.hypothesis.lower()
    assert cf_no_action.is_historical_fact is False

    cf_with_action = engine.evaluate_counterfactual(
        subject="cluster:k8s",
        current_trend="disk_filling_fast",
        proposed_action="purge_temporary_logs",  # "What if we take action X?"
        horizon_hours=24,
    )
    assert cf_with_action.is_hypothetical is True
    assert cf_with_action.label == "HYPOTHETICAL"
    assert "purge_temporary_logs" in cf_with_action.hypothesis
    assert cf_with_action.is_historical_fact is False
