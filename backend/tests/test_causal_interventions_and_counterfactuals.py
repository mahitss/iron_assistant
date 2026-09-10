"""Unit tests for Interventions, Counterfactuals, Experiments, and Safety Stops (Task 55)."""

import pytest

from app.causal.counterfactuals import CounterfactualEngine
from app.causal.experiments import CausalExperimentEngine
from app.causal.graph import CausalGraphEngine
from app.causal.hypotheses import HypothesisManager
from app.causal.interventions import InterventionEngine
from app.causal.safety import (
    HighRiskExperimentError,
    UnauthorizedInterventionError,
)
from app.causal.schemas import (
    CausalRelationshipType,
    CausalScope,
    HypothesisStatus,
    InterventionType,
)
from app.causal.simulation import CausalSimulationEngine


def test_intervention_authorization_and_safety_gate():
    """Prompt #43, #44: Causal engine cannot directly modify production without approval."""
    intv = InterventionEngine.create_intervention(
        target="prod-database-primary",
        change={"max_connections": 500},
        expected_effect={"latency_decreased": True},
        intervention_type=InterventionType.CONFIG_CHANGE,
        risk="HIGH",
    )

    # Attempting to authorize on production without approval must raise UnauthorizedInterventionError
    with pytest.raises(UnauthorizedInterventionError):
        InterventionEngine.validate_and_authorize(
            intervention=intv,
            is_production=True,
            approved_by=None,
        )

    # With operator approval, it passes
    authorized = InterventionEngine.validate_and_authorize(
        intervention=intv,
        is_production=True,
        approved_by="sre_oncall",
    )
    assert authorized.status == "AUTHORIZED"
    assert authorized.authorization["approved"] is True
    assert authorized.authorization["approved_by"] == "sre_oncall"


def test_intervention_effect_evaluation_and_hypothesis_update():
    """Prompt #46, #47, #48: Compare expected vs actual effect; update hypothesis."""
    hyp = HypothesisManager.create_hypothesis("cache_eviction", "high_latency", "miss rate surge", confidence=0.5)

    intv = InterventionEngine.create_intervention(
        target="redis_cache",
        change={"increase_ttl": 3600},
        expected_effect={"hit_rate_improved": True},
        intervention_type=InterventionType.CONFIG_CHANGE,
    )

    # Successful intervention matching expectation
    intv, ev, matched = InterventionEngine.evaluate_intervention_result(
        intervention=intv,
        actual_effect={"hit_rate_improved": True, "p99_ms": 120},
        hypothesis=hyp,
    )
    assert matched is True
    assert intv.status == "COMPLETED"
    assert hyp.confidence > 0.7
    assert hyp.status == HypothesisStatus.SUPPORTED

    # Failed intervention test
    hyp2 = HypothesisManager.create_hypothesis("network_route", "high_latency", "bad hop", confidence=0.4)
    intv2 = InterventionEngine.create_intervention(
        target="router",
        change={"switch_route": "bgp_2"},
        expected_effect={"loss_rate": 0.0},
    )
    intv2, ev2, matched2 = InterventionEngine.evaluate_intervention_result(
        intervention=intv2,
        actual_effect={"loss_rate": 0.08},
        hypothesis=hyp2,
    )
    assert matched2 is False
    assert hyp2.confidence < 0.3
    assert hyp2.status == HypothesisStatus.CONTRADICTED


def test_safety_stop_and_rollback():
    """Prompt #192, #193, #194: Stop intervention if safety threshold crossed; execute rollback."""
    metrics = {"error_rate": 0.08, "latency_p99_ms": 1500.0}
    stop_triggered, reason = InterventionEngine.check_safety_stop_condition(
        current_metrics=metrics,
        safety_thresholds={"error_rate": 0.05, "latency_p99_ms": 2000.0},
    )
    assert stop_triggered is True
    assert "error_rate" in reason

    intv = InterventionEngine.create_intervention("api_service", {"concurrency": 500}, {})
    rb = InterventionEngine.rollback_intervention(intv)
    assert intv.status == "ROLLED_BACK"
    assert rb["status"] == "ROLLED_BACK"


def test_controlled_experiment_contamination_and_safety():
    """Prompt #74, #76, #77: A/B experiments, contamination detection, high-risk approval."""
    # High risk experiment without approval must raise HighRiskExperimentError
    with pytest.raises(HighRiskExperimentError):
        CausalExperimentEngine.create_experiment(
            hypothesis_id="hyp_canary",
            treatment={"traffic": "v2"},
            control={"traffic": "v1"},
            metric="latency_p99",
            is_high_risk=True,
            authorization={"approved": False},
        )

    # Contamination detection
    has_contam, warnings = CausalExperimentEngine.check_contamination_risk(
        treatment={"cache_host": "redis-cluster-1.internal"},
        control={"cache_host": "redis-cluster-1.internal"},
    )
    assert has_contam is True
    assert any("cache" in w for w in warnings)


def test_counterfactual_scenario_and_simulation():
    """Prompt #63, #64, #65, #68: Counterfactuals and simulation are strictly hypothetical."""
    graph = CausalGraphEngine.create_graph(scope=CausalScope.SYSTEM)
    CausalGraphEngine.create_graph().edges
    from app.causal.edges import create_causal_edge

    edge = create_causal_edge("database_saturation", "api_gateway_latency", CausalRelationshipType.CAUSES, 0.8)
    CausalGraphEngine.upsert_edge(graph, edge)

    scenario = CounterfactualEngine.evaluate_what_if(
        question="What would have happened if database_saturation had not occurred?",
        removed_cause="database_saturation",
        baseline_state={"latency_p99": 2500.0},
        causal_graph=graph,
    )
    assert scenario.is_hypothetical is True  # Prompt #65: Must clearly label hypothetical conclusions
    assert "api_gateway_latency" in scenario.expected_difference["prevented_effects"]

    # Digital Twin simulation
    sim_result = CausalSimulationEngine.simulate_counterfactual(
        scenario=scenario,
        topology_nodes=["api_gateway", "database_cluster"],
        service_dependencies={"api_gateway": ["database_cluster"]},
    )
    assert sim_result["is_reality"] is False  # Prompt #68: Simulation is not reality
    assert "disclaimer" in sim_result
