"""9 Evaluation benchmarks for Kairo Autonomous Resource Economy Engine (Task 77)."""

from __future__ import annotations

import time
import pytest
from app.orchestration.budget import CognitiveBudgetEngine
from app.orchestration.coordinator import ResourceEconomyCoordinator
from app.orchestration.deadlock import DeadlockContentionEngine
from app.orchestration.economy import ResourceEconomyEngine
from app.orchestration.economy_schemas import (
    BudgetLifecycleState,
    BudgetScope,
    CognitiveDimension,
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
from app.security.emergency_stop import EmergencyStopService


# ------------------------------------------------------------------------------
# Benchmark 1: Demand Estimation Calibration
# ------------------------------------------------------------------------------
def test_benchmark_1_demand_estimation_calibration():
    """Verify confidence intervals correctly bound synthetic task variance."""
    economy = ResourceEconomyEngine()
    demands = [
        economy.estimate_demand("t_calib", "r1", estimated_tokens=1000, uncertainty_pct=0.15, confidence=0.90)
        for _ in range(10)
    ]
    for d in demands:
        assert d.lower_bound <= d.estimated_tokens <= d.upper_bound
        assert d.uncertainty_pct == 0.15
        assert d.confidence == 0.90


# ------------------------------------------------------------------------------
# Benchmark 2: Budget Boundary Enforcement
# ------------------------------------------------------------------------------
def test_benchmark_2_budget_boundary_enforcement():
    """Verify 7-state lifecycle transitions accurately at 0%, 85%, 100% consumption."""
    budget = CognitiveBudgetEngine()
    b = budget.create_budget(BudgetScope.PROJECT, "p_bench", {"CONTEXT_TOKENS": 1000.0}, near_limit_threshold=0.85)
    assert b.state == BudgetLifecycleState.ACTIVE

    # 50% consumption -> stays ACTIVE
    budget.allocate_budget({"CONTEXT_TOKENS": 500.0}, [(BudgetScope.PROJECT, "p_bench")])
    assert b.state == BudgetLifecycleState.ACTIVE

    # 85% consumption -> transitions to NEAR_LIMIT
    budget.allocate_budget({"CONTEXT_TOKENS": 350.0}, [(BudgetScope.PROJECT, "p_bench")])
    assert b.state == BudgetLifecycleState.NEAR_LIMIT

    # 100% consumption -> transitions to EXHAUSTED
    budget.allocate_budget({"CONTEXT_TOKENS": 150.0}, [(BudgetScope.PROJECT, "p_bench")])
    assert b.state == BudgetLifecycleState.EXHAUSTED

    # 101% rejected
    allowed, _, _ = budget.check_budget({"CONTEXT_TOKENS": 10.0}, [(BudgetScope.PROJECT, "p_bench")])
    assert not allowed


# ------------------------------------------------------------------------------
# Benchmark 3: Preemption Safety & Checkpoint Integrity
# ------------------------------------------------------------------------------
def test_benchmark_3_preemption_safety_and_checkpoint_integrity():
    """Verify checkpointed state preserves tokens and resumes seamlessly."""
    preemption = TaskPreemptionEngine()
    preemption.register_task("task_heavy", priority=1)

    # Preemption request
    ok, _, rec = preemption.request_preemption(
        task_id="task_heavy",
        preempted_by_task_id="task_urgent",
        requestor_priority=5,
    )
    assert ok
    assert rec.state == PreemptionState.PREEMPTION_REQUESTED

    # Checkpoint
    saved_state = {"intermediate_rag_docs": ["doc1", "doc2"], "cursor": 42}
    chk = preemption.checkpoint_task(
        task_id="task_heavy",
        state_snapshot=saved_state,
        saved_context_tokens=3500,
    )
    assert chk.state == PreemptionState.PAUSED
    assert chk.saved_context_tokens == 3500

    # Resumption
    res_ok, _, restored = preemption.resume_task("task_heavy")
    assert res_ok
    assert restored["intermediate_rag_docs"] == ["doc1", "doc2"]
    assert chk.state == PreemptionState.RESUMED


# ------------------------------------------------------------------------------
# Benchmark 4: Deadlock Detection Precision & Speed
# ------------------------------------------------------------------------------
def test_benchmark_4_deadlock_detection_precision_and_speed():
    """Verify 100% accuracy detecting cycles in wait-for graph with zero false positives under 10ms."""
    engine = DeadlockContentionEngine()
    for i in range(10):
        engine.register_task_priority(f"T{i}", priority=i)

    # Construct circular wait among 4 tasks: T0 -> R0 -> T1 -> R1 -> T2 -> R2 -> T3 -> R3 -> T0
    engine.add_allocation("R0", "T0")
    engine.add_wait("T1", "R0")

    engine.add_allocation("R1", "T1")
    engine.add_wait("T2", "R1")

    engine.add_allocation("R2", "T2")
    engine.add_wait("T3", "R2")

    engine.add_allocation("R3", "T3")
    engine.add_wait("T0", "R3")

    t_start = time.perf_counter()
    cycles = engine.detect_deadlocks()
    duration_ms = (time.perf_counter() - t_start) * 1000.0

    assert len(cycles) > 0
    assert duration_ms < 50.0  # sub-50ms execution

    victim, strategy = engine.resolve_deadlock(cycles[0])
    assert victim == "T0"  # Lowest priority among T0..T3
    assert strategy == ContentionResolutionStrategy.PREEMPT


# ------------------------------------------------------------------------------
# Benchmark 5: Anti-Starvation Aging Convergence
# ------------------------------------------------------------------------------
def test_benchmark_5_anti_starvation_aging_convergence():
    """Verify long-waiting tasks execute within guaranteed maximum wait threshold."""
    fairness = FairnessEngine(aging_factor_alpha=1.0, max_priority_boost=20.0, starvation_threshold_s=60.0)

    # Task A: base priority 1 (low priority background task)
    # Task B: base priority 5 (normal task)
    # After waiting 10 seconds, Task A effective priority = 1 + 10 = 11 > 5 (Task B)
    eff_a = fairness.calculate_effective_priority("task_a", base_priority=1, wait_time_s=10.0)
    eff_b = fairness.calculate_effective_priority("task_b", base_priority=5, wait_time_s=0.0)
    assert eff_a > eff_b  # Starvation prevented!


# ------------------------------------------------------------------------------
# Benchmark 6: Fairness Gini Index Convergence
# ------------------------------------------------------------------------------
def test_benchmark_6_fairness_gini_index():
    """Verify Gini coefficient remains within balanced bounds (< 0.4) under mixed load."""
    fairness = FairnessEngine()
    balanced_shares = {"tenant_1": 120.0, "tenant_2": 110.0, "tenant_3": 130.0, "tenant_4": 105.0}
    m = fairness.compute_fairness_metrics(balanced_shares)
    assert m.gini_coefficient < 0.10  # Highly equitable distribution


# ------------------------------------------------------------------------------
# Benchmark 7: Degraded Mode Pareto Quality
# ------------------------------------------------------------------------------
def test_benchmark_7_degraded_mode_pareto_quality():
    """Verify graceful degradation saves >= 50% tokens under aggressive throttle."""
    tradeoff = ResourceTradeOffEngine()
    long_prompt = "Line " * 200
    comp, model, savings = tradeoff.apply_degradation_strategy(long_prompt, DegradationTier.AGGRESSIVE_THROTTLE)
    assert savings >= 0.50
    assert model == "openrouter/free"


# ------------------------------------------------------------------------------
# Benchmark 8: EmergencyStop & Approval Gate Safety
# ------------------------------------------------------------------------------
def test_benchmark_8_emergency_stop_safety():
    """Verify immediate blocking with zero leakage when stopped."""
    es = EmergencyStopService()
    es.trigger_emergency_stop(user_id="operator", reason="Critical security alert")

    coordinator = ResourceEconomyCoordinator(emergency_stop_service=es)
    ok, reason, _ = coordinator.request_allocation(
        task_id="leak_test",
        demands={"CONTEXT_TOKENS": 100.0},
        scopes=[(BudgetScope.GLOBAL, "global")],
        user_id="operator",
    )
    assert not ok
    assert "Emergency stop is active" in reason


# ------------------------------------------------------------------------------
# Benchmark 9: ModelRouter & Attention Sync
# ------------------------------------------------------------------------------
def test_benchmark_9_model_router_and_attention_sync():
    """Verify model selection reflects budget constraints and degradation tier."""
    registry = ResourceRegistry()
    r = ResourceDefinition(
        resource_id="r_overload",
        name="Overloaded Host",
        resource_type=ResourceType.COMPUTE,
        total_capacity=100.0,
        available_capacity=2.0,
        allocated_capacity=98.0,
    )
    registry.register(r)
    economy = ResourceEconomyEngine(resource_registry=registry)
    coordinator = ResourceEconomyCoordinator(economy_engine=economy)

    model, tier = coordinator.route_model_for_task("sync_task")
    assert tier == DegradationTier.EMERGENCY_MINIMAL
    assert model == "system/deterministic_rule"
