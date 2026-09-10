"""Unit tests for counterfactuals, forecasting, comparison, ranking, Pareto optimization, and Monte Carlo (Task 56)."""


from app.simulation.comparison import ScenarioComparator
from app.simulation.counterfactuals import CounterfactualEngine
from app.simulation.forecasting import FutureStateForecaster
from app.simulation.monte_carlo import DistributionParam, MonteCarloEngine
from app.simulation.optimization import ParetoOptimizer
from app.simulation.schemas import (
    AssumptionImpact,
    AssumptionType,
    ScenarioAssumption,
    SimulatedIntervention,
    Simulation,
    SimulationObjective,
    SimulationStatus,
)


def test_counterfactual_engine_queries():
    engine = CounterfactualEngine()
    baseline = {
        "services": {
            "checkout": {"status": "DEGRADED", "replicas": 2},
        },
        "configs": {"timeout_sec": 30},
    }

    # 1. What if not happened
    orig_int = SimulatedIntervention(
        intervention_id="int_orig",
        target="configs.timeout_sec",
        operation="SET_TIMEOUT",
        before=15,
        hypothetical_after=30,
    )
    cf_not_happened = engine.what_if_never_happened(baseline, orig_int)
    assert cf_not_happened.counterfactual_state["configs"]["timeout_sec"] == 15
    assert cf_not_happened.query_type == "WHAT_IF_NOT_HAPPENED"

    # 2. What if changed instead
    alt_int = SimulatedIntervention(
        intervention_id="int_alt",
        target="configs.timeout_sec",
        operation="SET_TIMEOUT",
        before=15,
        hypothetical_after=45,
    )
    cf_alt = engine.what_if_changed_instead(baseline, orig_int, alt_int)
    assert cf_alt.counterfactual_state["configs"]["timeout_sec"] == 45

    # 3. What if we wait
    cf_wait = engine.what_if_we_wait(baseline, wait_horizon_seconds=600)
    assert "queue_depth" in cf_wait.counterfactual_state["services"]["checkout"]

    # 4. What if plan B
    plan_b_ints = [
        SimulatedIntervention(
            intervention_id="b1",
            target="services.checkout.replicas",
            operation="SCALE_REPLICAS",
            before=2,
            hypothetical_after=5,
        )
    ]
    cf_plan_b = engine.what_if_plan_b(baseline, plan_b_ints)
    assert cf_plan_b.counterfactual_state["services"]["checkout"]["replicas"] == 5


def test_future_state_forecaster():
    forecaster = FutureStateForecaster()
    baseline = {"cpu_percent": 40.0, "memory_percent": 50.0, "p95_latency_ms": 60.0}

    projections = forecaster.forecast_trajectory(baseline, hypothetical_interventions_count=0)
    assert len(projections) == 3
    horizons = [p.horizon_name for p in projections]
    assert "SHORT_TERM" in horizons
    assert "MEDIUM_TERM" in horizons
    assert "LONG_TERM" in horizons

    # Confidence decays over time
    short_p = next(p for p in projections if p.horizon_name == "SHORT_TERM")
    long_p = next(p for p in projections if p.horizon_name == "LONG_TERM")
    assert short_p.confidence > long_p.confidence


def test_pareto_optimizer_non_dominated_front():
    optimizer = ParetoOptimizer()
    objectives = [
        SimulationObjective(
            objective_id="obj_cost",
            metric="cost",
            direction="MINIMIZE",
        ),
        SimulationObjective(
            objective_id="obj_lat",
            metric="latency",
            direction="MINIMIZE",
        ),
    ]

    # Scenario A: cost=50, latency=100 (dominates C)
    # Scenario B: cost=80, latency=40  (trade-off vs A)
    # Scenario C: cost=90, latency=150 (dominated by both)
    scenario_metrics = {
        "scen_A": {"cost": 50.0, "latency": 100.0},
        "scen_B": {"cost": 80.0, "latency": 40.0},
        "scen_C": {"cost": 90.0, "latency": 150.0},
    }

    result = optimizer.find_pareto_frontier(scenario_metrics, objectives)
    assert "scen_A" in result.pareto_optimal_scenario_ids
    assert "scen_B" in result.pareto_optimal_scenario_ids
    assert "scen_C" in result.dominated_scenario_ids
    assert result.has_conflicting_objectives is True


def test_scenario_comparator_and_diff_conflict_detection():
    comparator = ScenarioComparator()

    assump1 = [
        ScenarioAssumption(
            assumption_id="a1",
            statement="Primary database replica has synchronous replication enabled.",
            assumption_type=AssumptionType.STATIC,
            impact=AssumptionImpact.MEDIUM,
            confidence=0.9,
        )
    ]
    assump2 = [
        ScenarioAssumption(
            assumption_id="a2",
            statement="Not primary database replica has synchronous replication enabled.",
            assumption_type=AssumptionType.STATIC,
            impact=AssumptionImpact.MEDIUM,
            confidence=0.9,
        )
    ]

    sim1 = Simulation(
        simulation_id="sim_1",
        source_snapshot_id="snap_1",
        scenario_id="scen_1",
        initial_state={},
        future_state={},
        diff={},
        effects=[],
        risks=[],
        assumptions=assump1,
        status=SimulationStatus.COMPLETED,
        confidence=0.9,
    )
    sim2 = Simulation(
        simulation_id="sim_2",
        source_snapshot_id="snap_1",
        scenario_id="scen_2",
        initial_state={},
        future_state={},
        diff={},
        effects=[],
        risks=[],
        assumptions=assump2,
        status=SimulationStatus.COMPLETED,
        confidence=0.9,
    )

    diff = comparator.diff_scenarios(sim1, sim2)
    assert diff.are_mergeable is False
    assert "conflicting assumption" in diff.merge_block_reason.lower()


def test_monte_carlo_engine_reproducibility():
    mc = MonteCarloEngine()
    param = DistributionParam(
        distribution_type="NORMAL",
        mean=0.0,
        std_dev=5.0,
    )

    res1 = mc.run_simulation(metric_name="latency", base_value=50.0, distribution=param, iterations=200, seed=123)
    res2 = mc.run_simulation(metric_name="latency", base_value=50.0, distribution=param, iterations=200, seed=123)

    assert res1.mean == res2.mean
    assert res1.p50 == res2.p50
    assert res1.p95 == res2.p95
    assert res1.is_reproducible is True
