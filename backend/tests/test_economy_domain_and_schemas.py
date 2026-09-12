"""Tests for domain schemas and contracts in Task 77."""

from __future__ import annotations

import pytest
from app.orchestration.economy_schemas import (
    BudgetLifecycleState,
    BudgetScope,
    CognitiveBudget,
    CognitiveDimension,
    ContentionResolutionStrategy,
    DeadlockCycle,
    DegradationTier,
    EconomyStatusSummary,
    FairnessMetrics,
    PreemptionPolicy,
    PreemptionState,
    ResourceDemand,
    SaturationState,
    TaskPreemptionRecord,
    TradeOffEvaluation,
)


def test_budget_scopes_and_states():
    """Verify all 5 scopes and 7 lifecycle states exist and serialize correctly."""
    assert len(BudgetScope) == 5
    assert set(BudgetScope) == {
        BudgetScope.REQUEST,
        BudgetScope.SESSION,
        BudgetScope.PROJECT,
        BudgetScope.USER,
        BudgetScope.GLOBAL,
    }

    assert len(BudgetLifecycleState) == 7
    assert set(BudgetLifecycleState) == {
        BudgetLifecycleState.CREATED,
        BudgetLifecycleState.ACTIVE,
        BudgetLifecycleState.NEAR_LIMIT,
        BudgetLifecycleState.EXHAUSTED,
        BudgetLifecycleState.RESET,
        BudgetLifecycleState.SUSPENDED,
        BudgetLifecycleState.EXPIRED,
    }


def test_cognitive_dimensions_and_degradation():
    """Verify 7 cognitive dimensions and 4 degradation tiers."""
    assert len(CognitiveDimension) == 7
    assert CognitiveDimension.CONTEXT_TOKENS.value == "CONTEXT_TOKENS"
    assert CognitiveDimension.MODEL_CALLS.value == "MODEL_CALLS"
    assert CognitiveDimension.REASONING_DEPTH.value == "REASONING_DEPTH"

    assert len(DegradationTier) == 4
    assert DegradationTier.FULL_FIDELITY.value == "FULL_FIDELITY"
    assert DegradationTier.MODERATE_COMPRESSION.value == "MODERATE_COMPRESSION"
    assert DegradationTier.AGGRESSIVE_THROTTLE.value == "AGGRESSIVE_THROTTLE"
    assert DegradationTier.EMERGENCY_MINIMAL.value == "EMERGENCY_MINIMAL"


def test_resource_demand_bounds():
    """Verify demand estimation bounds calculation."""
    demand = ResourceDemand(
        task_id="task_101",
        resource_id="res_gpu",
        estimated_tokens=2000,
        model_calls=2,
        expected_time_s=1.5,
        lower_bound=1700.0,
        upper_bound=2300.0,
        uncertainty_pct=0.15,
        confidence=0.90,
    )
    assert demand.task_id == "task_101"
    assert demand.lower_bound == 1700.0
    assert demand.upper_bound == 2300.0
    assert demand.confidence == 0.90


def test_cognitive_budget_schema():
    """Verify CognitiveBudget serialization and threshold defaults."""
    budget = CognitiveBudget(
        scope=BudgetScope.PROJECT,
        scope_id="proj_ai",
        limits={"CONTEXT_TOKENS": 100_000.0},
        consumed={"CONTEXT_TOKENS": 25_000.0},
        reserved={"CONTEXT_TOKENS": 5_000.0},
    )
    assert budget.scope == BudgetScope.PROJECT
    assert budget.near_limit_threshold == 0.85
    assert budget.consumed["CONTEXT_TOKENS"] == 25_000.0


def test_task_preemption_record():
    """Verify preemption state machine transitions."""
    rec = TaskPreemptionRecord(
        task_id="task_victim",
        priority=1,
        preempted_by_task_id="task_hero",
        state=PreemptionState.PAUSED,
        checkpoint_token="chk_abc123",
        saved_context_tokens=1500,
    )
    assert rec.state == PreemptionState.PAUSED
    assert rec.saved_context_tokens == 1500


def test_deadlock_cycle_schema():
    """Verify DeadlockCycle representation."""
    cycle = DeadlockCycle(
        involved_tasks=["task_a", "task_b"],
        involved_resources=["res_1", "res_2"],
        victim_task_id="task_a",
        resolved=True,
    )
    assert len(cycle.involved_tasks) == 2
    assert cycle.victim_task_id == "task_a"
    assert cycle.resolved is True


def test_fairness_and_tradeoff_schemas():
    """Verify FairnessMetrics and TradeOffEvaluation."""
    f = FairnessMetrics(
        gini_coefficient=0.15,
        max_min_ratio=1.5,
        starvation_count=0,
        average_wait_time_s=2.3,
    )
    assert f.gini_coefficient == 0.15
    assert f.starvation_count == 0

    ev = TradeOffEvaluation(
        candidate_id="cand_fast",
        quality_score=0.85,
        composite_score=0.88,
        degradation_tier=DegradationTier.MODERATE_COMPRESSION,
    )
    assert ev.composite_score == 0.88
    assert ev.degradation_tier == DegradationTier.MODERATE_COMPRESSION
