"""Unit tests for simulation scenarios, interventions, actions, and constraints (Task 56)."""


from app.simulation.actions import (
    FailoverDatabaseAction,
    InjectLatencyAction,
    KillServiceAction,
    RestartServiceAction,
    ScaleReplicasAction,
    UpdateConfigAction,
)
from app.simulation.constraints import ConstraintValidator
from app.simulation.interventions import InterventionExecutor
from app.simulation.scenarios import ScenarioManager
from app.simulation.schemas import (
    AssumptionImpact,
    AssumptionType,
    ScenarioAssumption,
    ScenarioType,
    SimulatedIntervention,
)


def test_scenario_creation_across_all_15_types():
    mgr = ScenarioManager()
    types_to_test = [
        ScenarioType.NO_CHANGE,
        ScenarioType.SINGLE_CHANGE,
        ScenarioType.MULTI_CHANGE,
        ScenarioType.FAILURE,
        ScenarioType.RECOVERY,
        ScenarioType.ROLLBACK,
        ScenarioType.SCALE_UP,
        ScenarioType.SCALE_DOWN,
        ScenarioType.MIGRATION,
        ScenarioType.DEPLOYMENT,
        ScenarioType.CONFIGURATION,
        ScenarioType.RESOURCE,
        ScenarioType.NETWORK,
        ScenarioType.DEPENDENCY,
        ScenarioType.CUSTOM,
    ]

    for st in types_to_test:
        scen = mgr.create_scenario(
            name=f"Test Scenario {st.value}",
            scenario_type=st,
            baseline_snapshot_id="snap_base_1",
        )
        assert scen.scenario_id.startswith("scen_")
        assert scen.scenario_type == st
        assert scen.version == 1
        assert len(scen.assumptions) >= 1


def test_assumption_tracking_and_critical_surfacing():
    mgr = ScenarioManager()
    assumptions = [
        ScenarioAssumption(
            assumption_id="a1",
            statement="Network connectivity to upstream payment processor is lossless.",
            assumption_type=AssumptionType.ESTIMATED,
            impact=AssumptionImpact.CRITICAL,
            confidence=0.75,
        ),
        ScenarioAssumption(
            assumption_id="a2",
            statement="Database connection pool size matches historical median.",
            assumption_type=AssumptionType.STATIC,
            impact=AssumptionImpact.LOW,
            confidence=0.95,
        ),
    ]

    scen = mgr.create_scenario(
        name="Critical Assumption Scenario",
        scenario_type=ScenarioType.CONFIGURATION,
        baseline_snapshot_id="snap_base_1",
        assumptions=assumptions,
    )

    criticals = mgr.get_critical_assumptions(scen.scenario_id)
    assert len(criticals) == 1
    assert criticals[0].assumption_id == "a1"


def test_sandboxed_action_execution():
    state = {
        "services": {
            "auth": {"status": "HEALTHY", "replicas": 2},
            "orders": {"status": "DEGRADED", "replicas": 3},
        },
        "databases": {
            "order_db": {"primary": "node_a"},
        },
        "configs": {"rate_limit": 100},
        "network_latency": {"gateway": 10.0},
    }

    # 1. Restart action
    state1 = RestartServiceAction().execute(state, service_name="orders")
    assert state1["services"]["orders"]["status"] == "RESTARTING"
    assert state1["services"]["orders"]["health"] == "HEALTHY"

    # 2. Kill action
    state2 = KillServiceAction().execute(state, service_name="auth")
    assert state2["services"]["auth"]["status"] == "DEAD"
    assert state2["services"]["auth"]["health"] == "CRITICAL"

    # 3. Scale action
    state3 = ScaleReplicasAction().execute(state, service_name="auth", replicas=8)
    assert state3["services"]["auth"]["replicas"] == 8

    # 4. Failover action
    state4 = FailoverDatabaseAction().execute(state, cluster_name="order_db", target_replica="node_b")
    assert state4["databases"]["order_db"]["primary"] == "node_b"

    # 5. Config update action
    state5 = UpdateConfigAction().execute(state, key="rate_limit", value=500)
    assert state5["configs"]["rate_limit"] == 500

    # 6. Inject latency action
    state6 = InjectLatencyAction().execute(state, node="gateway", latency_ms=45.0)
    assert state6["network_latency"]["gateway"] == 55.0


def test_intervention_executor_dot_notation():
    executor = InterventionExecutor()
    state = {
        "services": {
            "billing": {"replicas": 2, "env": "prod_sim"},
        }
    }
    interv = SimulatedIntervention(
        intervention_id="int_1",
        target="services.billing.replicas",
        operation="SCALE_REPLICAS",
        before={"replicas": 2},
        hypothetical_after=6,
    )

    mutations = executor.apply_to_state(state, interv)
    assert mutations["services"]["billing"]["replicas"] == 6


def test_resource_constraints_validation():
    validator = ConstraintValidator()

    # Within limits
    valid_state = {
        "services": {"checkout": {"replicas": 5}},
        "network_latency": {"gateway": 80.0},
    }
    res_valid = validator.validate_constraints(valid_state)
    assert res_valid.is_valid is True
    assert res_valid.status == "WITHIN_LIMITS"

    # Violated limits (replicas exceed 50, latency exceeds 2000ms)
    violated_state = {
        "services": {"checkout": {"replicas": 150}},
        "network_latency": {"gateway": 3500.0},
    }
    res_violated = validator.validate_constraints(violated_state)
    assert res_violated.is_valid is False
    assert res_violated.status == "VIOLATED"
    assert len(res_violated.violations) == 2
