"""Unit and integration tests for execution topology, wave calculation, barriers, and multi-agent coordination (Task 59)."""

import pytest

from app.orchestration.coordination import CoordinationEngine
from app.orchestration.safety import (
    OrchestrationSafetyError,
    SeparationOfDutiesViolationError,
    verify_separation_of_duties,
)
from app.orchestration.schemas import (
    ProviderAssignment,
    TaskCapabilityRequirement,
)
from app.orchestration.topology import TopologyEngine


def test_topology_dag_and_execution_waves():
    """Verify execution topology correctly generates discrete waves and dependency edges."""
    engine = TopologyEngine()

    req_a = TaskCapabilityRequirement(task_id="task_A", title="Build")
    req_b = TaskCapabilityRequirement(task_id="task_B", title="Test 1")
    req_c = TaskCapabilityRequirement(task_id="task_C", title="Test 2")
    req_d = TaskCapabilityRequirement(task_id="task_D", title="Deploy")

    reqs = [req_a, req_b, req_c, req_d]
    asgns = [
        ProviderAssignment(task_id="task_A", provider_name="Builder", capability_id="cap_build"),
        ProviderAssignment(task_id="task_B", provider_name="Tester1", capability_id="cap_test"),
        ProviderAssignment(task_id="task_C", provider_name="Tester2", capability_id="cap_test"),
        ProviderAssignment(task_id="task_D", provider_name="Deployer", capability_id="cap_dep"),
    ]

    # Dependencies: B depends on A, C depends on A, D depends on B and C
    deps = {
        "task_B": ["task_A"],
        "task_C": ["task_A"],
        "task_D": ["task_B", "task_C"],
    }

    topo = engine.build_topology(reqs, asgns, deps)

    assert len(topo.nodes) == 4
    assert len(topo.edges) == 4
    assert len(topo.execution_waves) == 3

    # Wave 1: task_A
    wave_1_tasks = [t["task_id"] for t in topo.execution_waves[0]["tasks"]]
    assert wave_1_tasks == ["task_A"]

    # Wave 2: task_B and task_C (parallel)
    wave_2_tasks = [t["task_id"] for t in topo.execution_waves[1]["tasks"]]
    assert set(wave_2_tasks) == {"task_B", "task_C"}
    assert topo.execution_waves[1]["is_parallel"] is True

    # Wave 3: task_D
    wave_3_tasks = [t["task_id"] for t in topo.execution_waves[2]["tasks"]]
    assert wave_3_tasks == ["task_D"]

    # Synchronization barrier should exist for task_D
    assert len(topo.synchronization_barriers) == 1
    barrier = topo.synchronization_barriers[0]
    assert barrier["target_task"] == "task_D"
    assert set(barrier["converging_tasks"]) == {"task_B", "task_C"}


def test_topology_cycle_detection():
    """Verify cyclic task dependencies are detected and rejected."""
    engine = TopologyEngine()
    req_a = TaskCapabilityRequirement(task_id="task_A")
    req_b = TaskCapabilityRequirement(task_id="task_B")

    # Cycle: A depends on B, B depends on A
    deps = {
        "task_A": ["task_B"],
        "task_B": ["task_A"],
    }

    with pytest.raises(OrchestrationSafetyError, match="Cycle detected in task dependencies"):
        engine.build_topology([req_a, req_b], [], deps)


def test_coordination_synchronization_barrier():
    """Verify barrier condition requires all converging tasks to be completed."""
    coord = CoordinationEngine()
    converging = ["task_1", "task_2", "task_3"]

    # Partial completion
    assert coord.check_synchronization_barrier("barrier_01", converging, {"task_1", "task_2"}) is False

    # Full completion
    assert coord.check_synchronization_barrier("barrier_01", converging, {"task_1", "task_2", "task_3"}) is True


def test_coordination_handoff_and_schema_validation():
    """Verify explicit data handoffs between agents with schema enforcement."""
    coord = CoordinationEngine()

    schema = {"required": ["artifact_url", "checksum"]}
    valid_payload = {"artifact_url": "s3://builds/app.tar.gz", "checksum": "abc123"}
    invalid_payload = {"artifact_url": "s3://builds/app.tar.gz"}

    res = coord.validate_handoff("BuildAgent", "DeployAgent", valid_payload, expected_schema=schema)
    assert res["status"] == "VALIDATED"

    with pytest.raises(OrchestrationSafetyError, match="Missing required field 'checksum'"):
        coord.validate_handoff("BuildAgent", "DeployAgent", invalid_payload, expected_schema=schema)


def test_separation_of_duties_defense():
    """Test Invariants 4 & 61-62: Creator cannot approve or verify their own high-impact actions."""
    # Self-approval violation
    with pytest.raises(SeparationOfDutiesViolationError, match="Self-approval defense triggered"):
        verify_separation_of_duties(
            creator="AgentAlpha",
            approver="AgentAlpha",
            is_high_impact=True,
        )

    # Self-verification violation
    with pytest.raises(SeparationOfDutiesViolationError, match="Self-verification defense triggered"):
        verify_separation_of_duties(
            creator="AgentAlpha",
            approver="AdminUser",
            executor="WorkerX",
            verifier="WorkerX",
            is_high_impact=True,
        )

    # Distinct actors pass
    assert verify_separation_of_duties(
        creator="AgentAlpha",
        reviewer="SecurityAgent",
        approver="AdminUser",
        executor="WorkerX",
        verifier="VerifierAgent",
        is_high_impact=True,
    ) is True


def test_agent_disagreement_resolution():
    """Verify agent opinions are evaluated by specialist weighting without fake consensus."""
    coord = CoordinationEngine()

    opinions = [
        {"agent": "GeneralistBot", "conclusion": "ALLOW", "confidence": 0.6, "is_specialist": False},
        {"agent": "SecuritySpecialist", "conclusion": "BLOCK", "confidence": 0.85, "is_specialist": True},
    ]

    resolution = coord.resolve_agent_disagreement(opinions)
    assert resolution["resolved"] is True
    # SecuritySpecialist has higher confidence and specialist weighting -> winner is BLOCK
    assert resolution["winner"]["conclusion"] == "BLOCK"
    assert len(resolution["all_opinions"]) == 2  # Preserves all individual outputs
