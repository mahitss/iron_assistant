"""Integration and safety tests for ResourceEconomyCoordinator (Task 77)."""

from __future__ import annotations

import pytest
from app.orchestration.budget import CognitiveBudgetEngine
from app.orchestration.coordinator import ResourceEconomyCoordinator
from app.orchestration.economy import ResourceEconomyEngine
from app.orchestration.economy_schemas import BudgetScope, CognitiveDimension, DegradationTier
from app.orchestration.resource_registry import ResourceRegistry
from app.orchestration.schemas import ResourceDefinition, ResourceType
from app.security.emergency_stop import EmergencyStopService


def test_emergency_stop_blocks_allocations_and_preemptions():
    """Verify that EmergencyStop halts all autonomous resource allocations and preemptions."""
    es = EmergencyStopService()
    es.trigger_emergency_stop(user_id="alice", reason="Security containment test")

    coordinator = ResourceEconomyCoordinator(emergency_stop_service=es)
    assert coordinator.is_stopped(user_id="alice")

    # 1. Allocation blocked
    success, reason, _ = coordinator.request_allocation(
        task_id="task_1",
        demands={"CONTEXT_TOKENS": 1000.0},
        scopes=[(BudgetScope.GLOBAL, "global")],
        user_id="alice",
    )
    assert not success
    assert "Emergency stop is active" in reason

    # 2. Preemption blocked
    preempt_ok, preempt_reason, _ = coordinator.request_safe_preemption(
        task_id="task_victim",
        preempted_by_task_id="task_hero",
        requestor_priority=5,
        user_id="alice",
    )
    assert not preempt_ok
    assert "Emergency stop active" in preempt_reason


def test_hierarchical_budget_inheritance():
    """Verify multi-tier budget checking: Request -> Project -> Global."""
    budget = CognitiveBudgetEngine()
    # Project budget: max 5000 tokens
    budget.create_budget(BudgetScope.PROJECT, "proj_1", {"CONTEXT_TOKENS": 5000.0})
    # Request budget: max 2000 tokens
    budget.create_budget(BudgetScope.REQUEST, "req_1", {"CONTEXT_TOKENS": 2000.0})

    coordinator = ResourceEconomyCoordinator(budget_engine=budget)

    # Request within request limit (1500 <= 2000) and project limit (1500 <= 5000) -> Allowed
    ok, reason, _ = coordinator.request_allocation(
        task_id="t1",
        demands={"CONTEXT_TOKENS": 1500.0},
        scopes=[(BudgetScope.REQUEST, "req_1"), (BudgetScope.PROJECT, "proj_1"), (BudgetScope.GLOBAL, "global")],
    )
    assert ok

    # Request exceeds request limit (1000 + 1500 = 2500 > 2000) -> Rejected
    fail_ok, fail_reason, _ = coordinator.request_allocation(
        task_id="t2",
        demands={"CONTEXT_TOKENS": 1000.0},
        scopes=[(BudgetScope.REQUEST, "req_1"), (BudgetScope.PROJECT, "proj_1"), (BudgetScope.GLOBAL, "global")],
    )
    assert not fail_ok
    assert "exceeds dimension 'CONTEXT_TOKENS'" in fail_reason


def test_model_routing_under_degraded_tiers():
    """Verify ModelRouter integration recommending model based on economy saturation."""
    registry = ResourceRegistry()
    res = ResourceDefinition(
        resource_id="res_sat",
        name="Compute Node",
        resource_type=ResourceType.COMPUTE,
        total_capacity=100.0,
        available_capacity=10.0,
        allocated_capacity=90.0,
    )
    registry.register(res)
    economy = ResourceEconomyEngine(resource_registry=registry)
    coordinator = ResourceEconomyCoordinator(economy_engine=economy)

    model_id, tier = coordinator.route_model_for_task("task_x", capability="general")
    assert tier == DegradationTier.AGGRESSIVE_THROTTLE
    assert model_id == "openrouter/free"


def test_coordinator_deadlock_resolution():
    """Verify coordinator detects and breaks wait-for cycles."""
    coordinator = ResourceEconomyCoordinator()
    coordinator.deadlock.register_task_priority("task_a", 1)
    coordinator.deadlock.register_task_priority("task_b", 4)

    coordinator.deadlock.add_allocation("res_1", "task_a")
    coordinator.deadlock.add_wait("task_b", "res_1")

    coordinator.deadlock.add_allocation("res_2", "task_b")
    coordinator.deadlock.add_wait("task_a", "res_2")

    resolutions = coordinator.check_and_resolve_deadlocks()
    assert len(resolutions) == 1
    assert resolutions[0]["victim_task_id"] == "task_a"
