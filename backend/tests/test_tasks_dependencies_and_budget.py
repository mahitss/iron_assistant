"""Tests for DAG dependency resolution, cycle detection, and runtime budget limits (Spec 9, 10, 14, 15)."""

import pytest
from app.tasks.budget import BudgetExceededError, TaskBudgetEnforcer
from app.tasks.dependencies import (
    CircularDependencyError,
    DependencyResolver,
    MissingDependencyError,
)
from app.tasks.schemas import (
    StepStatus,
    TaskBudget,
    TaskRiskLevel,
    TaskStepSchema,
)


def test_topological_sort_valid_dag():
    """Verify linear and branching DAGs resolve in valid execution order."""
    s1 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=1, id="s1", title="Step 1", objective="Inspect", dependencies=[])
    s2 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=2, id="s2", title="Step 2", objective="Analyze", dependencies=["s1"])
    s3 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=3, id="s3", title="Step 3", objective="Fix", dependencies=["s2"])

    order = DependencyResolver.validate_dag([s1, s2, s3])
    assert order == ["s1", "s2", "s3"]


def test_circular_dependency_rejection():
    """Verify circular references (A -> B -> A) are detected and rejected (Spec 10)."""
    s1 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=1, id="step_A", title="A", objective="A", dependencies=["step_B"])
    s2 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=2, id="step_B", title="B", objective="B", dependencies=["step_A"])

    with pytest.raises(CircularDependencyError):
        DependencyResolver.validate_dag([s1, s2])


def test_self_dependency_rejection():
    """Verify a step depending on itself is rejected."""
    s1 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=1, id="step_A", title="A", objective="A", dependencies=["step_A"])
    with pytest.raises(CircularDependencyError):
        DependencyResolver.validate_dag([s1])


def test_missing_dependency_rejection():
    """Verify reference to a non-existent step ID is rejected."""
    s1 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=1, id="s1", title="A", objective="A", dependencies=["non_existent_step"])
    with pytest.raises(MissingDependencyError):
        DependencyResolver.validate_dag([s1])


def test_get_ready_steps_resolution():
    """Verify ready step resolution based on completed dependencies and parallelism limits."""
    s1 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=1, id="s1", title="S1", objective="Read A", dependencies=[], risk_level=TaskRiskLevel.READ)
    s2 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=2, id="s2", title="S2", objective="Read B", dependencies=[], risk_level=TaskRiskLevel.READ)
    s3 = TaskStepSchema(task_id="t1", plan_id="p1", sequence=3, id="s3", title="S3", objective="Synthesize", dependencies=["s1", "s2"], risk_level=TaskRiskLevel.READ)

    all_steps = [s1, s2, s3]

    # Initially, with 0 completed steps, both s1 and s2 should be ready (parallel reads)
    ready = DependencyResolver.get_ready_steps(all_steps, completed_step_ids=set(), max_parallel=4)
    ready_ids = {s.id for s in ready}
    assert ready_ids == {"s1", "s2"}

    # When s1 is complete, s2 is still pending, but s3 is not ready yet
    ready = DependencyResolver.get_ready_steps(all_steps, completed_step_ids={"s1"}, max_parallel=4)
    assert [s.id for s in ready] == ["s2"]

    # When both s1 and s2 are complete, s3 becomes ready
    ready = DependencyResolver.get_ready_steps(all_steps, completed_step_ids={"s1", "s2"}, max_parallel=4)
    assert [s.id for s in ready] == ["s3"]


def test_budget_step_limit_enforcement():
    """Verify runtime enforcement halts when step budget is exhausted (Spec 14, 15)."""
    budget = TaskBudget(max_steps=3, max_tool_calls=50, max_duration_seconds=300)
    enforcer = TaskBudgetEnforcer(budget)

    enforcer.record_step(1)
    enforcer.record_step(1)
    enforcer.record_step(1)  # 3/3 used

    with pytest.raises(BudgetExceededError) as exc_info:
        enforcer.record_step(1)  # 4th step violates budget
    assert "step" in str(exc_info.value)


def test_budget_tool_call_limit_enforcement():
    """Verify runtime halts when tool call budget is exceeded."""
    budget = TaskBudget(max_steps=20, max_tool_calls=2)
    enforcer = TaskBudgetEnforcer(budget)

    enforcer.record_tool_calls(2)

    with pytest.raises(BudgetExceededError) as exc_info:
        enforcer.record_tool_calls(1)
    assert "tool_call" in str(exc_info.value)


def test_budget_cost_limit_enforcement():
    """Verify runtime halts when cost budget in USD is exceeded."""
    budget = TaskBudget(max_cost_usd=1.0)
    enforcer = TaskBudgetEnforcer(budget)

    enforcer.record_cost(0.75)
    assert enforcer.current_budget.cost_used_usd == 0.75

    with pytest.raises(BudgetExceededError) as exc_info:
        enforcer.record_cost(0.50)  # Total $1.25 > $1.00
    assert "cost_usd" in str(exc_info.value)
