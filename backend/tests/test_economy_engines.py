"""Unit tests for core engines: economy, budget, preemption, deadlock, fairness, and trade-offs (Task 77)."""

from __future__ import annotations

import pytest
from app.orchestration.budget import CognitiveBudgetEngine
from app.orchestration.deadlock import DeadlockContentionEngine
from app.orchestration.economy import ResourceEconomyEngine
from app.orchestration.economy_schemas import (
    BudgetLifecycleState,
    BudgetScope,
    ContentionResolutionStrategy,
    DegradationTier,
    PreemptionPolicy,
    PreemptionState,
    SaturationState,
)
from app.orchestration.fairness import FairnessEngine
from app.orchestration.preemption import TaskPreemptionEngine
from app.orchestration.resource_registry import ResourceRegistry
from app.orchestration.schemas import ResourceDefinition, ResourceType
from app.orchestration.tradeoff import ResourceTradeOffEngine


# ------------------------------------------------------------------------------
# 1. Economy Engine Tests
# ------------------------------------------------------------------------------

def test_economy_demand_estimation():
    economy = ResourceEconomyEngine()
    demand = economy.estimate_demand(
        task_id="t1",
        resource_id="res_gpu",
        estimated_tokens=1000,
        uncertainty_pct=0.20,
    )
    assert demand.estimated_tokens == 1000
    assert demand.lower_bound == 800.0
    assert demand.upper_bound == 1200.0


def test_economy_saturation_and_degradation():
    registry = ResourceRegistry()
    r = ResourceDefinition(
        resource_id="r1",
        name="Compute Pool",
        resource_type=ResourceType.COMPUTE,
        total_capacity=100.0,
        available_capacity=10.0,
        allocated_capacity=90.0,
    )
    registry.register(r)
    economy = ResourceEconomyEngine(resource_registry=registry)

    sat_pct, state = economy.compute_economy_saturation()
    assert sat_pct == 0.90
    assert state == SaturationState.OVERCOMMITTED

    tier = economy.recommend_degradation_tier(sat_pct)
    assert tier == DegradationTier.AGGRESSIVE_THROTTLE


# ------------------------------------------------------------------------------
# 2. Cognitive Budget Engine Tests
# ------------------------------------------------------------------------------

def test_cognitive_budget_lifecycle_and_near_limit():
    engine = CognitiveBudgetEngine()
    budget = engine.create_budget(
        scope=BudgetScope.PROJECT,
        scope_id="proj_x",
        limits={"CONTEXT_TOKENS": 10_000.0},
        near_limit_threshold=0.80,
    )
    assert budget.state == BudgetLifecycleState.ACTIVE

    # Allocate 85% -> transitions to NEAR_LIMIT
    engine.allocate_budget({"CONTEXT_TOKENS": 8500.0}, [(BudgetScope.PROJECT, "proj_x")])
    b = engine.get_budget(BudgetScope.PROJECT, "proj_x")
    assert b.consumed["CONTEXT_TOKENS"] == 8500.0
    assert b.state == BudgetLifecycleState.NEAR_LIMIT

    # Allocate remaining -> EXHAUSTED
    engine.allocate_budget({"CONTEXT_TOKENS": 1500.0}, [(BudgetScope.PROJECT, "proj_x")])
    b = engine.get_budget(BudgetScope.PROJECT, "proj_x")
    assert b.state == BudgetLifecycleState.EXHAUSTED

    # Excess allocation rejected
    allowed, reason, _ = engine.check_budget({"CONTEXT_TOKENS": 1.0}, [(BudgetScope.PROJECT, "proj_x")])
    assert not allowed
    assert "EXHAUSTED" in reason


def test_cognitive_budget_reservation_and_reset():
    engine = CognitiveBudgetEngine()
    engine.create_budget(
        scope=BudgetScope.SESSION,
        scope_id="sess_1",
        limits={"MODEL_CALLS": 10.0},
    )

    # Reserve 5 calls
    success = engine.reserve_budget({"MODEL_CALLS": 5.0}, [(BudgetScope.SESSION, "sess_1")])
    assert success
    b = engine.get_budget(BudgetScope.SESSION, "sess_1")
    assert b.reserved["MODEL_CALLS"] == 5.0

    # Release reservation
    engine.release_reservation({"MODEL_CALLS": 5.0}, [(BudgetScope.SESSION, "sess_1")])
    assert b.reserved["MODEL_CALLS"] == 0.0

    # Consume and reset
    engine.allocate_budget({"MODEL_CALLS": 8.0}, [(BudgetScope.SESSION, "sess_1")])
    assert b.consumed["MODEL_CALLS"] == 8.0

    reset_success = engine.reset_budget(BudgetScope.SESSION, "sess_1")
    assert reset_success
    assert b.consumed["MODEL_CALLS"] == 0.0
    assert b.state == BudgetLifecycleState.ACTIVE


# ------------------------------------------------------------------------------
# 3. Preemption Engine Tests
# ------------------------------------------------------------------------------

def test_preemption_lifecycle_and_priority_inversion():
    engine = TaskPreemptionEngine()
    engine.register_task("task_low", priority=1)

    # Higher priority preempts lower priority
    ok, msg, rec = engine.request_preemption(
        task_id="task_low",
        preempted_by_task_id="task_high",
        requestor_priority=3,
        policy=PreemptionPolicy.COOPERATIVE,
    )
    assert ok
    assert rec.state == PreemptionState.PREEMPTION_REQUESTED

    # Checkpoint task
    rec = engine.checkpoint_task(
        task_id="task_low",
        state_snapshot={"step": 4, "state": "partial"},
        saved_context_tokens=1200,
    )
    assert rec.state == PreemptionState.PAUSED
    assert rec.checkpoint_token is not None

    # Resume task
    res_ok, _, snapshot = engine.resume_task("task_low")
    assert res_ok
    assert snapshot["step"] == 4
    assert rec.state == PreemptionState.RESUMED

    # Inversion rejection: priority 1 cannot preempt priority 3
    engine.register_task("task_p3", priority=3)
    inv_ok, inv_reason, _ = engine.request_preemption(
        task_id="task_p3",
        preempted_by_task_id="task_p1",
        requestor_priority=1,
    )
    assert not inv_ok
    assert "Priority inversion rejected" in inv_reason


# ------------------------------------------------------------------------------
# 4. Deadlock Engine Tests
# ------------------------------------------------------------------------------

def test_deadlock_detection_and_resolution():
    engine = DeadlockContentionEngine()
    engine.register_task_priority("T1", priority=1)
    engine.register_task_priority("T2", priority=5)

    # Circular wait: T1 holds R1, waits for R2. T2 holds R2, waits for R1.
    engine.add_allocation("R1", "T1")
    engine.add_wait("T1", "R2")

    engine.add_allocation("R2", "T2")
    engine.add_wait("T2", "R1")

    cycles = engine.detect_deadlocks()
    assert len(cycles) > 0

    victim, strategy = engine.resolve_deadlock(cycles[0])
    # T1 has lower priority (1 vs 5) -> selected as victim
    assert victim == "T1"
    assert strategy == ContentionResolutionStrategy.PREEMPT

    # Graph is now acyclic
    remaining = engine.detect_deadlocks()
    assert len(remaining) == 0


# ------------------------------------------------------------------------------
# 5. Fairness Engine Tests
# ------------------------------------------------------------------------------

def test_fairness_anti_starvation_and_gini():
    engine = FairnessEngine(aging_factor_alpha=0.5, max_priority_boost=10.0, starvation_threshold_s=30.0)

    # Base priority 2 + 10s wait * 0.5 = 7.0
    eff_p = engine.calculate_effective_priority("t_starve", base_priority=2, wait_time_s=10.0)
    assert eff_p == 7.0

    # Max boost cap
    eff_max = engine.calculate_effective_priority("t_starve", base_priority=2, wait_time_s=100.0)
    assert eff_max == 12.0  # 2 + 10

    # Starvation threshold
    assert not engine.is_starving("t_starve", wait_time_s=25.0)
    assert engine.is_starving("t_starve", wait_time_s=35.0)

    # Gini coefficient: perfect equality -> 0.0
    metrics_equal = engine.compute_fairness_metrics({"u1": 100.0, "u2": 100.0, "u3": 100.0})
    assert metrics_equal.gini_coefficient == 0.0

    # Extreme inequality -> Gini > 0.4
    metrics_skew = engine.compute_fairness_metrics({"u1": 1000.0, "u2": 1.0, "u3": 1.0})
    assert metrics_skew.gini_coefficient > 0.4


# ------------------------------------------------------------------------------
# 6. Trade-Off Engine Tests
# ------------------------------------------------------------------------------

def test_tradeoff_pareto_scoring_and_compression():
    engine = ResourceTradeOffEngine()
    eval_res = engine.evaluate_tradeoff(
        candidate_id="cand_1",
        quality_score=0.95,
        latency_ms=150.0,
        financial_cost=0.02,
        risk_score=0.05,
        resource_usage_score=0.20,
    )
    assert eval_res.composite_score > 0.80

    prompt = "This is a detailed reasoning request with complex instructions.\nStep 1: Check.\nStep 2: Act.\nStep 3: Verify."
    c_full, m_full, s_full = engine.apply_degradation_strategy(prompt, DegradationTier.FULL_FIDELITY)
    assert s_full == 0.0
    assert m_full == "openrouter/reasoning"

    c_mod, m_mod, s_mod = engine.apply_degradation_strategy(prompt, DegradationTier.MODERATE_COMPRESSION)
    assert s_mod == 0.30
    assert m_mod == "openrouter/fast"

    c_min, m_min, s_min = engine.apply_degradation_strategy(prompt, DegradationTier.EMERGENCY_MINIMAL)
    assert s_min == 0.90
    assert m_min == "system/deterministic_rule"
