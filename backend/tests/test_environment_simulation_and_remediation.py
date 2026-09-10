"""Unit tests for What-If Simulation, Governed Remediation, and Auto-Healing Loops (Task 54)."""

import pytest

from app.environment.auto_healing import AutoHealingGovernor
from app.environment.edges import create_environment_edge
from app.environment.nodes import create_environment_node
from app.environment.remediation import RemediationManager
from app.environment.safety import (
    ProductionSafetyViolationError,
    RemediationLoopError,
    UnverifiedRollbackError,
)
from app.environment.schemas import (
    ImpactLevel,
    NodeType,
    RelationshipType,
)
from app.environment.topology import TopologyGraph
from app.environment.what_if import WhatIfSimulator


def test_what_if_simulation_is_strictly_hypothetical():
    """Prompt #211, #212, #213: Support 'What happens if service X goes down?' labeled hypothetical."""
    n_db = create_environment_node("db_orders", NodeType.DATABASE, "db:orders", "Orders DB")
    n_svc = create_environment_node("svc_checkout", NodeType.SERVICE, "s:checkout", "Checkout")
    n_gw = create_environment_node("svc_gateway", NodeType.SERVICE, "s:gateway", "Gateway")

    e1 = create_environment_edge("svc_checkout", RelationshipType.READS_FROM, "db_orders", provenance={"source": "trace"})
    e2 = create_environment_edge("svc_gateway", RelationshipType.CALLS, "svc_checkout", provenance={"source": "trace"})

    topology = TopologyGraph(
        nodes={"db_orders": n_db, "svc_checkout": n_svc, "svc_gateway": n_gw},
        edges={e1.edge_id: e1, e2.edge_id: e2},
    )

    result = WhatIfSimulator.simulate_node_failure(target_node_id="db_orders", topology=topology)

    assert result.is_hypothetical is True
    assert result.target_node == "db_orders"
    assert "svc_checkout" in result.affected_nodes
    assert "svc_gateway" in result.affected_nodes
    assert result.potential_impact in (ImpactLevel.MEDIUM, ImpactLevel.HIGH)


def test_production_remediation_requires_verified_rollback():
    """Prompt #110, #111, #224, #225: Production remediation requires verified rollback target."""
    # Production change plan without verified rollback target is rejected
    with pytest.raises(UnverifiedRollbackError):
        RemediationManager.create_change_plan(
            target="svc_payment",
            current_state={"version": "1.4.0"},
            desired_state={"version": "1.5.0"},
            risk=ImpactLevel.HIGH,
            dependencies=["db_payment"],
            rollback_target=None,
            rollback_verified=False,
            is_production=True,
        )

    # With verified rollback target, plan is generated cleanly
    plan = RemediationManager.create_change_plan(
        target="svc_payment",
        current_state={"version": "1.4.0"},
        desired_state={"version": "1.5.0"},
        risk=ImpactLevel.HIGH,
        dependencies=["db_payment"],
        rollback_target={"version": "1.4.0", "digest": "sha256:abc1234"},
        rollback_verified=True,
        is_production=True,
    )
    assert plan.target == "svc_payment"
    assert plan.rollback_verified is True
    assert plan.approved is False  # Must be approved before execution


def test_state_race_invalidates_remediation_plan():
    """Prompt #129, #130: Stale plan detection when environment state changes before action."""
    plan = RemediationManager.create_change_plan(
        target="svc_auth",
        current_state={"replica_count": 3, "version": "1.0"},
        desired_state={"replica_count": 5, "version": "1.0"},
        risk=ImpactLevel.LOW,
        dependencies=[],
        rollback_target={"replica_count": 3},
        rollback_verified=True,
        is_production=False,
    )

    # If state changed to replica_count = 4 before action, plan is invalidated
    current_runtime_mutated = {"replica_count": 4, "version": "1.0"}
    with pytest.raises(ProductionSafetyViolationError) as exc_info:
        RemediationManager.validate_plan_for_execution(
            plan=plan,
            is_production=False,
            current_observed_state=current_runtime_mutated,
        )
    assert "State race detected" in str(exc_info.value)


def test_auto_healing_budget_and_loop_prevention():
    """Prompt #231, #232: Governed auto-healing prevents repeated loops via attempt budget."""
    governor = AutoHealingGovernor(max_attempts_per_resource=3)
    plan = RemediationManager.create_change_plan(
        target="svc_cache",
        current_state={"status": "DEGRADED"},
        desired_state={"status": "HEALTHY"},
        risk=ImpactLevel.LOW,
        dependencies=[],
    )

    # Attempt 1, 2, 3 succeed
    assert governor.request_auto_healing("svc_cache", plan) is True
    assert governor.request_auto_healing("svc_cache", plan) is True
    assert governor.request_auto_healing("svc_cache", plan) is True

    # Attempt 4 exceeds budget and raises RemediationLoopError
    with pytest.raises(RemediationLoopError) as exc_info:
        governor.request_auto_healing("svc_cache", plan)
    assert "Auto-healing loop detected" in str(exc_info.value)

    # Recording success resets budget
    governor.record_healing_success("svc_cache")
    assert governor.request_auto_healing("svc_cache", plan) is True
