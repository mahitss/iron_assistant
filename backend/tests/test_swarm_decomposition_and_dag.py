"""Unit tests for Swarm Task Decomposition, DAG Construction, Cycle Detection, and Parallel Batching (Task 64)."""

import pytest

from app.swarm.decomposition import TaskDecomposer, TaskDecompositionError
from app.swarm.safety import SwarmSafetyError, SwarmSpawnLimiter
from app.swarm.schemas import CollectiveObjective, SwarmTopology


def test_star_topology_decomposition():
    decomposer = TaskDecomposer()
    objective = CollectiveObjective(
        goal="Design high-availability event bus for real-time sensor ingestion",
        risk_level="HIGH",
        priority="HIGH",
    )

    dag = decomposer.decompose(objective, topology=SwarmTopology.STAR)

    assert dag.objective_id == objective.objective_id
    assert len(dag.tasks) == 7
    assert len(dag.parallel_groups) >= 3

    # Group 1 should contain parallel independent specialists
    first_group = dag.parallel_groups[0]
    assert len(first_group) >= 4

    # Synthesis should depend on first group tasks
    synth_task = next(t for t in dag.tasks if t.role_needed == "SYNTHESIZER")
    for dep in synth_task.dependencies:
        assert dep in first_group

    # Verification should depend on synthesis
    verif_task = next(t for t in dag.tasks if t.role_needed == "VERIFIER")
    assert synth_task.task_id in verif_task.dependencies


def test_pipeline_topology_decomposition():
    decomposer = TaskDecomposer()
    objective = CollectiveObjective(
        goal="Multi-stage code refactoring and regression review",
        risk_level="MEDIUM",
        priority="MEDIUM",
    )

    dag = decomposer.decompose(objective, topology=SwarmTopology.PIPELINE)

    assert len(dag.tasks) == 5
    # In a pipeline, every stage after the first has exactly 1 dependency
    for i in range(1, len(dag.tasks)):
        assert len(dag.tasks[i].dependencies) == 1
        assert dag.tasks[i - 1].task_id in dag.tasks[i].dependencies


def test_debate_topology_decomposition():
    decomposer = TaskDecomposer()
    objective = CollectiveObjective(
        goal="Resolve architectural contention between SQL vs NoSQL for tenant state storage",
        risk_level="HIGH",
        priority="HIGH",
    )

    dag = decomposer.decompose(objective, topology=SwarmTopology.DEBATE)

    roles = [t.role_needed for t in dag.tasks]
    assert "ARCHITECT" in roles
    assert "CRITIC" in roles
    assert "SYNTHESIZER" in roles
    assert "VERIFIER" in roles


def test_dag_cycle_detection_strictly_forbidden():
    decomposer = TaskDecomposer()

    # Artificially test cycle detection
    cyclic_dep_map = {
        "task_1": ["task_2"],
        "task_2": ["task_3"],
        "task_3": ["task_1"],  # Loop!
    }

    with pytest.raises(TaskDecompositionError) as exc_info:
        decomposer._validate_no_cycles(cyclic_dep_map)

    assert "Circular dependency cycle detected" in str(exc_info.value)


def test_critical_path_computation():
    decomposer = TaskDecomposer()
    objective = CollectiveObjective(
        goal="Benchmark database sharding strategy",
        risk_level="HIGH",
        priority="HIGH",
    )

    dag = decomposer.decompose(objective, topology=SwarmTopology.STAR)

    assert len(dag.critical_path) >= 3
    # Check that critical path tasks have is_critical_path == True
    cp_tasks = [t for t in dag.tasks if t.task_id in dag.critical_path]
    for t in cp_tasks:
        assert t.is_critical_path is True


def test_spawn_limiter_bounds_enforcement():
    strict_limiter = SwarmSpawnLimiter(max_tasks=3)
    decomposer = TaskDecomposer(limiter=strict_limiter)

    objective = CollectiveObjective(
        goal="Expansive objective requiring too many tasks",
        risk_level="HIGH",
        priority="HIGH",
    )

    # Star topology produces 7 tasks, which exceeds strict limit of 3
    with pytest.raises(SwarmSafetyError) as exc_info:
        decomposer.decompose(objective, topology=SwarmTopology.STAR)

    assert "Task limit exceeded" in str(exc_info.value)
