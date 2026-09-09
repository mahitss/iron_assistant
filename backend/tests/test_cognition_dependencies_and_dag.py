"""Unit tests for Dependency DAG, cycle detection, and parallel execution safety (Task 41)."""

import pytest
from app.cognition.dependencies import (
    DependencyCycleError,
    DependencyGraph,
)
from app.cognition.steps import PlanStep, StepRiskLevel, StepStatus


def test_acyclic_dag_topological_sort():
    s1 = PlanStep(step_id="step_1", plan_id="p1", sequence=1, objective="Inspect state", action="inspect")
    s2 = PlanStep(step_id="step_2", plan_id="p1", sequence=2, objective="Apply patch", action="patch", dependencies=["step_1"])
    s3 = PlanStep(step_id="step_3", plan_id="p1", sequence=3, objective="Verify", action="verify", dependencies=["step_2"])

    graph = DependencyGraph([s1, s2, s3])
    graph.validate_acyclic()
    order = graph.topological_sort()

    assert order == ["step_1", "step_2", "step_3"]


def test_dependency_cycle_detection():
    # A -> B -> C -> A cycle
    s1 = PlanStep(step_id="step_a", plan_id="p1", sequence=1, objective="A", action="act_a", dependencies=["step_c"])
    s2 = PlanStep(step_id="step_b", plan_id="p1", sequence=2, objective="B", action="act_b", dependencies=["step_a"])
    s3 = PlanStep(step_id="step_c", plan_id="p1", sequence=3, objective="C", action="act_c", dependencies=["step_b"])

    graph = DependencyGraph([s1, s2, s3])
    with pytest.raises(DependencyCycleError) as exc_info:
        graph.validate_acyclic()
    assert "Dependency cycle detected" in str(exc_info.value)


def test_parallel_safety_read_steps():
    # Multiple read-only steps on the same or different resources can execute in parallel
    s1 = PlanStep(step_id="s1", plan_id="p1", sequence=1, objective="Read logs", action="read_logs", risk=StepRiskLevel.READ, inputs={"file": "app.log"})
    s2 = PlanStep(step_id="s2", plan_id="p1", sequence=1, objective="Read metrics", action="read_metrics", risk=StepRiskLevel.READ, inputs={"file": "app.log"})

    graph = DependencyGraph([s1, s2])
    tiers = graph.compute_parallel_execution_tiers()
    # Both s1 and s2 should be runnable together in the same tier
    assert len(tiers) == 1
    assert set(tiers[0]) == {"s1", "s2"}


def test_resource_conflict_forces_serialization():
    # Two write steps modifying the same file cannot run in parallel and must be serialized
    s1 = PlanStep(step_id="w1", plan_id="p1", sequence=1, objective="Patch config", action="write", risk=StepRiskLevel.WRITE, inputs={"file": "config.json"})
    s2 = PlanStep(step_id="w2", plan_id="p1", sequence=1, objective="Update config", action="write", risk=StepRiskLevel.WRITE, inputs={"file": "config.json"})

    graph = DependencyGraph([s1, s2])
    tiers = graph.compute_parallel_execution_tiers()
    # Conflicting steps targeting the same resource must be split across different execution groups
    assert len(tiers) == 2
    flattened = [item for sublist in tiers for item in sublist]
    assert set(flattened) == {"w1", "w2"}
