"""Tests for Isolated Counterfactual Scenario Sandboxes (Task 65)."""

from app.foresight.scenarios import ScenarioEngine
from app.foresight.schemas import (
    ForesightEntity,
    ForesightHorizon,
    ScenarioType,
)


def test_scenario_sandbox_isolation_invariant():
    """Verify SIMULATED != PRODUCTION invariant (Spec 24, 25).

    Mutations or interventions evaluated in scenario branches MUST NEVER
    mutate production entity objects.
    """
    engine = ScenarioEngine()

    prod_entities = {
        "db_aurora": ForesightEntity(
            entity_id="db_aurora",
            type="database",
            name="Aurora DB",
            state="HEALTHY",
            attributes={"connections": 150},
        )
    }

    branch = engine.create_scenario_branch(
        name="Catastrophic Connection Saturation",
        scenario_type=ScenarioType.ADVERSE,
        horizon=ForesightHorizon.MID_FUTURE_1M,
        current_entities=prod_entities,
        interventions=["Inject 10x query load", "Set connection pool to max"],
    )

    # Simulated branch records expected changes
    assert len(branch.interventions) == 2
    assert len(branch.expected_changes) > 0

    # Invariant: Production entity is strictly unmutated
    assert prod_entities["db_aurora"].state == "HEALTHY"
    assert prod_entities["db_aurora"].attributes["connections"] == 150


def test_scenario_types_and_sensitivity_scoring():
    """Verify scenario generation across canonical types and sensitivity analysis (Spec 23, 26)."""
    engine = ScenarioEngine()

    ents = {
        "svc_api": ForesightEntity(entity_id="svc_api", type="service", name="API Gateway", state="HEALTHY")
    }

    scenarios = [
        engine.create_scenario_branch(
            "Baseline Trend", ScenarioType.BASELINE, ForesightHorizon.MID_FUTURE_1M, ents
        ),
        engine.create_scenario_branch(
            "High Adoption", ScenarioType.OPTIMISTIC, ForesightHorizon.MID_FUTURE_1M, ents
        ),
        engine.create_scenario_branch(
            "Severe Outage", ScenarioType.DISRUPTION, ForesightHorizon.MID_FUTURE_1M, ents
        ),
        engine.create_scenario_branch(
            "Rapid Failover", ScenarioType.RECOVERY, ForesightHorizon.MID_FUTURE_1M, ents
        ),
    ]

    for scn in scenarios:
        assert 0.0 <= scn.confidence <= 1.0
        assert 0.0 <= scn.sensitivity_score <= 1.0
        assert not scn.is_stale


def test_scenario_invalidation_on_assumption_change():
    """Verify scenarios are invalidated when core premise assumptions change (Spec 27)."""
    engine = ScenarioEngine()
    ents = {"s1": ForesightEntity(entity_id="s1", type="service", name="Service 1", state="HEALTHY")}

    branch = engine.create_scenario_branch(
        name="Legacy Migration",
        scenario_type=ScenarioType.BASELINE,
        horizon=ForesightHorizon.MID_FUTURE_1M,
        current_entities=ents,
        assumptions=["Legacy monolith runs on PHP 7.4 until Q3"],
    )

    invalidated = engine.invalidate_on_assumption_change("monolith runs on PHP 7.4")
    assert branch.scenario_id in invalidated

    retrieved = engine.get_scenario(branch.scenario_id)
    assert retrieved.is_stale is True
