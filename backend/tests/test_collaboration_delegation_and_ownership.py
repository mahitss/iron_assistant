"""Tests for Task Ownership, Backpressure, Spawn Limits, and Loop Detection (Task 44)."""

import pytest
from app.agents.delegation import (
    DelegationError,
    DelegationLoopError,
    DelegationManager,
    OwnershipCollisionError,
    SpawnLimitExceededError,
)


def test_single_task_ownership():
    """Each delegated subtask must have exactly one primary owner."""
    mgr = DelegationManager()
    mgr.delegate(
        parent_task_id="goal_root",
        subtask_id="sub_task_1",
        objective="Analyze logs",
        agent_id="agent_1",
        contract_id="ct_1",
        role="ANALYST",
    )

    owner = mgr.get_subtask_owner("sub_task_1")
    assert owner == "agent_1"

    # Second agent attempting to claim ownership of the same subtask raises OwnershipCollisionError
    with pytest.raises(OwnershipCollisionError):
        mgr.delegate(
            parent_task_id="goal_root",
            subtask_id="sub_task_1",
            objective="Analyze logs concurrently",
            agent_id="agent_2",
            contract_id="ct_2",
            role="ANALYST",
        )


def test_backpressure_and_spawn_limits():
    """Agent spawn limit prevents uncontrolled subagent spawning."""
    mgr = DelegationManager(max_concurrent_agents=3)

    for i in range(3):
        mgr.delegate(
            parent_task_id="goal_root",
            subtask_id=f"task_{i}",
            objective=f"Objective {i}",
            agent_id=f"agent_{i}",
            contract_id=f"ct_{i}",
            role="RESEARCHER",
        )

    # 4th concurrent agent exceeds backpressure limit
    with pytest.raises(SpawnLimitExceededError):
        mgr.delegate(
            parent_task_id="goal_root",
            subtask_id="task_overflow",
            objective="Objective overflow",
            agent_id="agent_overflow",
            contract_id="ct_overflow",
            role="RESEARCHER",
        )


def test_delegation_loop_detection():
    """Detects circular delegation A -> B -> A and halts recursion."""
    mgr = DelegationManager()

    # Root -> Agent A
    mgr.delegate(
        parent_task_id="root",
        subtask_id="task_a",
        objective="Subtask A",
        agent_id="agent_A",
        contract_id="ct_a",
        role="CODER",
    )

    # Agent A -> Agent B
    mgr.delegate(
        parent_task_id="agent_A",
        subtask_id="task_b",
        objective="Subtask B",
        agent_id="agent_B",
        contract_id="ct_b",
        role="REVIEWER",
    )

    # Agent B attempting to delegate back to Agent A detects loop
    with pytest.raises(DelegationLoopError):
        mgr.delegate(
            parent_task_id="agent_B",
            subtask_id="task_c",
            objective="Subtask C back to A",
            agent_id="agent_A",
            contract_id="ct_c",
            role="CODER",
        )


def test_spawn_depth_protection():
    """Limits nested delegation depth."""
    mgr = DelegationManager(max_depth=2)

    # Depth 1: Root -> A
    mgr.delegate(
        parent_task_id="root",
        subtask_id="sub_1",
        objective="Depth 1",
        agent_id="agent_1",
        contract_id="ct_1",
        role="PLANNER",
    )

    # Depth 2: A -> B
    mgr.delegate(
        parent_task_id="agent_1",
        subtask_id="sub_2",
        objective="Depth 2",
        agent_id="agent_2",
        contract_id="ct_2",
        role="CODER",
    )

    # Depth 3: B -> C exceeds depth
    with pytest.raises(DelegationError):
        mgr.delegate(
            parent_task_id="agent_2",
            subtask_id="sub_3",
            objective="Depth 3",
            agent_id="agent_3",
            contract_id="ct_3",
            role="TESTER",
        )
