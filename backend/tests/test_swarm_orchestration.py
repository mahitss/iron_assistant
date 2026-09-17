"""Unit and invariant tests for Kairo Swarm Orchestration & Multi-Agent Collaboration (Task 96)."""

import asyncio
from datetime import UTC, datetime, timedelta
import pytest

from app.security.emergency_stop import get_emergency_stop_service
from app.swarm.blackboard import BoundedBlackboard
from app.swarm.orchestration_domain import (
    AgentIdentity,
    AgentLifecycleState,
    AgentMessage,
    AgentRole,
    AgentTask,
    DelegationLimits,
    MessageType,
    StallState,
    TaskDependencyState,
    ValidationStatus,
    _now_utc,
)
from app.swarm.orchestration_service import (
    SwarmOrchestrationService,
    get_swarm_orchestration_service,
)
from app.swarm.supervision import SwarmSupervisionEngine


# ------------------------------------------------------------------------------
# 1. 14-State Agent Lifecycle Invariants
# ------------------------------------------------------------------------------

def test_agent_lifecycle_transitions_valid():
    """Verify standard legal lifecycle progressions."""
    agent = AgentIdentity(
        agent_id="agent-worker-01",
        session_id="swarm-sess-01",
        role=AgentRole.RESEARCHER,
    )
    assert agent.lifecycle_state == AgentLifecycleState.CREATED
    assert not agent.is_active

    agent.transition_to(AgentLifecycleState.QUEUED, reason="Enqueued by supervisor")
    assert agent.lifecycle_state == AgentLifecycleState.QUEUED

    agent.transition_to(AgentLifecycleState.INITIALIZING, reason="Allocating resources")
    assert agent.lifecycle_state == AgentLifecycleState.INITIALIZING

    agent.transition_to(AgentLifecycleState.RUNNING, reason="Execution dispatched")
    assert agent.lifecycle_state == AgentLifecycleState.RUNNING
    assert agent.is_active

    agent.transition_to(AgentLifecycleState.WAITING, reason="Awaiting dependency")
    assert agent.lifecycle_state == AgentLifecycleState.WAITING

    agent.transition_to(AgentLifecycleState.RUNNING, reason="Dependency satisfied")
    assert agent.lifecycle_state == AgentLifecycleState.RUNNING

    agent.transition_to(AgentLifecycleState.COMPLETED, reason="Objective achieved")
    assert agent.lifecycle_state == AgentLifecycleState.COMPLETED
    assert agent.is_terminal
    assert not agent.is_active
    assert len(agent.history) == 6


def test_agent_lifecycle_invalid_transition_fails():
    """Verify illegal transitions are strictly rejected."""
    agent = AgentIdentity(
        agent_id="agent-worker-02",
        session_id="swarm-sess-01",
        role=AgentRole.CODER,
    )
    # CREATED -> COMPLETED is illegal (must initialize/run first)
    with pytest.raises(ValueError, match="Illegal agent state transition"):
        agent.transition_to(AgentLifecycleState.COMPLETED)

    # Move to terminal COMPLETED
    agent.transition_to(AgentLifecycleState.QUEUED)
    agent.transition_to(AgentLifecycleState.INITIALIZING)
    agent.transition_to(AgentLifecycleState.RUNNING)
    agent.transition_to(AgentLifecycleState.COMPLETED)

    # Terminal state cannot transition anywhere
    with pytest.raises(ValueError, match="Illegal agent state transition"):
        agent.transition_to(AgentLifecycleState.RUNNING)


# ------------------------------------------------------------------------------
# 2. Strict DAG Validation & Cycle Detection
# ------------------------------------------------------------------------------

def test_dag_cycle_detection():
    """Verify that cyclic task dependencies are detected and rejected via Kahn's algorithm."""
    supervision = SwarmSupervisionEngine()
    limits = DelegationLimits(max_depth=3, max_total_agents=10)

    # Create cycle: Task A -> Task B -> Task C -> Task A
    tasks = {
        "task-A": AgentTask(
            task_id="task-A",
            session_id="sess-01",
            objective="Analyze data",
            role_needed=AgentRole.ANALYST,
            dependencies=["task-C"],
        ),
        "task-B": AgentTask(
            task_id="task-B",
            session_id="sess-01",
            objective="Verify schema",
            role_needed=AgentRole.VALIDATOR,
            dependencies=["task-A"],
        ),
        "task-C": AgentTask(
            task_id="task-C",
            session_id="sess-01",
            objective="Compile summary",
            role_needed=AgentRole.SYNTHESIZER,
            dependencies=["task-B"],
        ),
    }

    errors = supervision.validate_task_graph(tasks, limits)
    assert len(errors) > 0
    assert any("Cycle detected" in err for err in errors)


def test_dag_depth_limit_enforcement():
    """Verify delegation depth exceeding limit is flagged."""
    supervision = SwarmSupervisionEngine()
    limits = DelegationLimits(max_depth=2)

    # Chain of 3 deep: t1 -> t2 -> t3
    tasks = {
        "t1": AgentTask(task_id="t1", session_id="s1", objective="Root", role_needed=AgentRole.PLANNER),
        "t2": AgentTask(task_id="t2", session_id="s1", parent_task_id="t1", objective="Sub 1", role_needed=AgentRole.RESEARCHER),
        "t3": AgentTask(task_id="t3", session_id="s1", parent_task_id="t2", objective="Sub 2", role_needed=AgentRole.ANALYST),
        "t4": AgentTask(task_id="t4", session_id="s1", parent_task_id="t3", objective="Sub 3 (depth 3)", role_needed=AgentRole.VALIDATOR),
    }

    errors = supervision.validate_task_graph(tasks, limits)
    assert any("exceeds maximum allowed depth" in err for err in errors)


# ------------------------------------------------------------------------------
# 3. Controlled Delegation & Anti-Privilege Escalation
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delegation_scope_confinement():
    """Verify child agent cannot exceed parent capability scope."""
    service = SwarmOrchestrationService()
    session = await service.create_swarm(objective="Test Delegation Scope")

    # Spawn parent agent with restricted read-only capability
    parent = await service.spawn_agent(
        session_id=session.session_id,
        role=AgentRole.RESEARCHER,
        capability_scope=["web_search", "document_read"],
    )

    # Attempt delegation where child requests unauthorized "system_exec" capability
    with pytest.raises(PermissionError, match="Privilege escalation prevented"):
        await service.delegate_subtask(
            parent_agent_id=parent.agent_id,
            objective="Execute external script",
            role_needed=AgentRole.EXECUTOR,
            allowed_capabilities=["web_search", "system_exec"],
        )


@pytest.mark.asyncio
async def test_successful_scoped_delegation():
    """Verify legitimate child delegation within parent authority bounds."""
    service = SwarmOrchestrationService()
    session = await service.create_swarm(objective="Legitimate Delegation Test")

    parent = await service.spawn_agent(
        session_id=session.session_id,
        role=AgentRole.RESEARCHER,
        capability_scope=["web_search", "document_read"],
    )

    child_task = await service.delegate_subtask(
        parent_agent_id=parent.agent_id,
        objective="Read document index",
        role_needed=AgentRole.ANALYST,
        allowed_capabilities=["document_read"],
    )

    assert child_task.task_id is not None
    assert child_task.parent_task_id == parent.task_id
    assert child_task.required_capabilities == ["document_read"]

    child_agent = service.get_agent(child_task.assigned_agent_id)
    assert child_agent is not None
    assert child_agent.parent_agent_id == parent.agent_id
    assert child_agent.capability_scope == ["document_read"]


# ------------------------------------------------------------------------------
# 4. Bounded Blackboard & Shared Fact Invariants
# ------------------------------------------------------------------------------

def test_bounded_blackboard_limits():
    """Verify shared blackboard caps total entries at 500 to prevent memory exhaustion."""
    bb = BoundedBlackboard(max_entries=10)
    for i in range(15):
        bb.post(
            topic="benchmarks",
            content={"run": i, "score": 90 + i},
            author_agent_id=f"agent-{i}",
        )

    # Cap must hold
    assert len(bb) == 10
    entries = bb.query(topic="benchmarks")
    assert len(entries) == 10
    # Oldest (run 0..4) evicted, runs 5..14 retained
    assert entries[0].content["run"] == 5
    assert entries[-1].content["run"] == 14


# ------------------------------------------------------------------------------
# 5. Supervision & Stall Assessment
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_supervision_stall_detection():
    """Verify stall detector flags agents blocked or failing repeatedly."""
    service = SwarmOrchestrationService()
    session = await service.create_swarm(objective="Supervision Test")

    agent = await service.spawn_agent(
        session_id=session.session_id,
        role=AgentRole.CODER,
    )

    # Artificially set state to WAITING with an old timestamp
    agent.lifecycle_state = AgentLifecycleState.WAITING
    agent.updated_at = datetime.now(UTC) - timedelta(seconds=120)

    stalls = await service.check_supervision(session.session_id)
    assert agent.agent_id in stalls
    assert stalls[agent.agent_id] in (StallState.STALLED, StallState.SLOW)


# ------------------------------------------------------------------------------
# 6. Action Execution Boundary & Task 95 Integration
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_action_routes_through_action_transaction():
    """Verify agent actions are wrapped in formal ActionTransactions."""
    service = SwarmOrchestrationService()
    session = await service.create_swarm(objective="Action Boundary Test")

    agent = await service.spawn_agent(
        session_id=session.session_id,
        role=AgentRole.EXECUTOR,
        capability_scope=["fs.write_file"],
    )

    # Agent requests action
    txn = await service.execute_agent_action(
        agent_id=agent.agent_id,
        action_reference="fs.write_file",
        target={"type": "FILESYSTEM_PATH", "resource_id": "test_output.json"},
        parameters={"data": "test_payload"},
    )

    assert txn.transaction_id is not None
    assert txn.capability_id == "fs.write_file"
    assert txn.target.resource_id == "test_output.json"


# ------------------------------------------------------------------------------
# 7. Emergency Stop Fail-Closed Invariant
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emergency_stop_halts_swarm_operations():
    """Verify active EmergencyStop blocks all new agent spawning and actions fail-closed."""
    service = SwarmOrchestrationService()
    estop = get_emergency_stop_service()

    estop.trigger_emergency_stop(reason="Safety alarm triggered for test")

    try:
        # Spawning agent under EmergencyStop must fail
        with pytest.raises(Exception, match="Emergency Stop is currently ACTIVE"):
            await service.spawn_agent(
                session_id="sess-blocked",
                role=AgentRole.RESEARCHER,
            )
    finally:
        estop.reset_emergency_stop()
