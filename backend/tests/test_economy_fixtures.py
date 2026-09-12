"""12 Synthetic test fixtures and environments for Autonomous Resource Economy and Cognitive Budgets (Task 77)."""

from __future__ import annotations

from typing import Any

from app.orchestration.budget import CognitiveBudgetEngine
from app.orchestration.coordinator import ResourceEconomyCoordinator
from app.orchestration.deadlock import DeadlockContentionEngine
from app.orchestration.economy import ResourceEconomyEngine
from app.orchestration.economy_schemas import (
    BudgetLifecycleState,
    BudgetScope,
    CognitiveDimension,
    DegradationTier,
    PreemptionPolicy,
    SaturationState,
)
from app.orchestration.fairness import FairnessEngine
from app.orchestration.preemption import TaskPreemptionEngine
from app.orchestration.resource_registry import ResourceRegistry
from app.orchestration.schemas import ResourceDefinition, ResourceStatus, ResourceType
from app.orchestration.tradeoff import ResourceTradeOffEngine
from app.security.emergency_stop import EmergencyStopService


def create_fixture_ample_headroom() -> ResourceEconomyCoordinator:
    """Fixture 1: Ample headroom environment with high capacity and low utilization."""
    registry = ResourceRegistry()
    res = ResourceDefinition(
        resource_id="res_compute_high",
        name="High Capacity GPU Node",
        resource_type=ResourceType.COMPUTE,
        total_capacity=1000.0,
        available_capacity=900.0,
        allocated_capacity=100.0,
        reserved_capacity=0.0,
    )
    registry.register(res)

    economy = ResourceEconomyEngine(resource_registry=registry)
    budget = CognitiveBudgetEngine()
    budget.create_budget(
        scope=BudgetScope.PROJECT,
        scope_id="proj_headroom",
        limits={
            CognitiveDimension.CONTEXT_TOKENS.value: 500_000.0,
            CognitiveDimension.MODEL_CALLS.value: 10_000.0,
        },
    )
    return ResourceEconomyCoordinator(economy_engine=economy, budget_engine=budget)


def create_fixture_token_exhaustion() -> ResourceEconomyCoordinator:
    """Fixture 2: Hard token budget exhaustion environment."""
    budget = CognitiveBudgetEngine()
    b = budget.create_budget(
        scope=BudgetScope.REQUEST,
        scope_id="req_exhausted",
        limits={CognitiveDimension.CONTEXT_TOKENS.value: 2000.0},
    )
    # Fully consume budget
    budget.allocate_budget(
        {"CONTEXT_TOKENS": 2000.0},
        [(BudgetScope.REQUEST, "req_exhausted")],
    )
    return ResourceEconomyCoordinator(budget_engine=budget)


def create_fixture_model_call_saturation() -> ResourceEconomyCoordinator:
    """Fixture 3: Model call quota saturated, triggering degraded mode."""
    budget = CognitiveBudgetEngine()
    budget.create_budget(
        scope=BudgetScope.SESSION,
        scope_id="sess_saturated",
        limits={CognitiveDimension.MODEL_CALLS.value: 5.0},
        near_limit_threshold=0.8,
    )
    budget.allocate_budget(
        {"MODEL_CALLS": 4.5},
        [(BudgetScope.SESSION, "sess_saturated")],
    )
    return ResourceEconomyCoordinator(budget_engine=budget)


def create_fixture_high_priority_preemption() -> ResourceEconomyCoordinator:
    """Fixture 4: Low-priority background task executing, high-priority request arriving."""
    preemption = TaskPreemptionEngine()
    # Task 1: Background scraper (Priority 1)
    preemption.register_task(task_id="task_bg_worker", priority=1)
    return ResourceEconomyCoordinator(preemption_engine=preemption)


def create_fixture_contention() -> ResourceEconomyCoordinator:
    """Fixture 5: Multi-task resource contention over finite execution slots."""
    registry = ResourceRegistry()
    res = ResourceDefinition(
        resource_id="res_slot_limited",
        name="Limited Execution Slots",
        resource_type=ResourceType.EXECUTION_SLOT,
        total_capacity=2.0,
        available_capacity=0.0,
        allocated_capacity=2.0,
    )
    registry.register(res)
    economy = ResourceEconomyEngine(resource_registry=registry)
    return ResourceEconomyCoordinator(economy_engine=economy)


def create_fixture_circular_deadlock() -> ResourceEconomyCoordinator:
    """Fixture 6: Circular wait deadlock cycle (T1 -> R1 -> T2 -> R2 -> T1)."""
    deadlock = DeadlockContentionEngine()
    deadlock.register_task_priority("task_alpha", priority=1)
    deadlock.register_task_priority("task_beta", priority=3)

    # R1 held by task_alpha, task_beta waiting for R1
    deadlock.add_allocation("res_db_lock", "task_alpha")
    deadlock.add_wait("task_beta", "res_db_lock")

    # R2 held by task_beta, task_alpha waiting for R2
    deadlock.add_allocation("res_cache_lock", "task_beta")
    deadlock.add_wait("task_alpha", "res_cache_lock")

    return ResourceEconomyCoordinator(deadlock_engine=deadlock)


def create_fixture_starvation_scenario() -> ResourceEconomyCoordinator:
    """Fixture 7: Starvation scenario where low-priority task waits in queue."""
    fairness = FairnessEngine(aging_factor_alpha=1.0, max_priority_boost=15.0, starvation_threshold_s=30.0)
    return ResourceEconomyCoordinator(fairness_engine=fairness)


def create_fixture_multitenant_fairshare() -> ResourceEconomyCoordinator:
    """Fixture 8: Multi-tenant workload with uneven distribution to compute Gini index."""
    fairness = FairnessEngine()
    budget = CognitiveBudgetEngine()
    budget.create_budget(BudgetScope.USER, "user_heavy", {"CONTEXT_TOKENS": 100_000.0})
    budget.allocate_budget({"CONTEXT_TOKENS": 90_000.0}, [(BudgetScope.USER, "user_heavy")])

    budget.create_budget(BudgetScope.USER, "user_light", {"CONTEXT_TOKENS": 100_000.0})
    budget.allocate_budget({"CONTEXT_TOKENS": 10_000.0}, [(BudgetScope.USER, "user_light")])

    return ResourceEconomyCoordinator(budget_engine=budget, fairness_engine=fairness)


def create_fixture_degraded_mode() -> ResourceEconomyCoordinator:
    """Fixture 9: Severe resource constraint (>90% saturation) requiring degraded tier."""
    registry = ResourceRegistry()
    res = ResourceDefinition(
        resource_id="res_constrained",
        name="Overcommitted Node",
        resource_type=ResourceType.COMPUTE,
        total_capacity=100.0,
        available_capacity=5.0,
        allocated_capacity=95.0,
    )
    registry.register(res)
    economy = ResourceEconomyEngine(resource_registry=registry)
    return ResourceEconomyCoordinator(economy_engine=economy)


def create_fixture_emergency_stop_active() -> ResourceEconomyCoordinator:
    """Fixture 10: System where EmergencyStop is active."""
    es = EmergencyStopService()
    es.trigger_emergency_stop(user_id="user_safety", reason="Test Emergency Stop Triggered")
    return ResourceEconomyCoordinator(emergency_stop_service=es)


def create_fixture_cooperative_preemption() -> ResourceEconomyCoordinator:
    """Fixture 11: Cooperative preemption with state checkpointing."""
    preemption = TaskPreemptionEngine()
    preemption.register_task("task_coop_target", priority=2)
    return ResourceEconomyCoordinator(preemption_engine=preemption)


def create_fixture_hierarchy_inheritance() -> ResourceEconomyCoordinator:
    """Fixture 12: Multi-tier budget hierarchy (Global -> Project -> Request)."""
    budget = CognitiveBudgetEngine()
    budget.create_budget(
        scope=BudgetScope.PROJECT,
        scope_id="proj_omega",
        limits={CognitiveDimension.CONTEXT_TOKENS.value: 20_000.0},
    )
    budget.create_budget(
        scope=BudgetScope.REQUEST,
        scope_id="req_omega_sub",
        limits={CognitiveDimension.CONTEXT_TOKENS.value: 5_000.0},
    )
    return ResourceEconomyCoordinator(budget_engine=budget)
