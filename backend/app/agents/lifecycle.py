"""Agent lifecycle state machine and transition rules (Task 44)."""

from __future__ import annotations

import enum
import logging

logger = logging.getLogger("kairo.agents.lifecycle")


class AgentLifecycleState(str, enum.Enum):
    """Authoritative lifecycle states for an agent instance (Spec 9)."""

    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    DRAINING = "DRAINING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TERMINATED = "TERMINATED"


VALID_LIFECYCLE_TRANSITIONS: dict[AgentLifecycleState, set[AgentLifecycleState]] = {
    AgentLifecycleState.CREATED: {AgentLifecycleState.READY, AgentLifecycleState.TERMINATED},
    AgentLifecycleState.READY: {AgentLifecycleState.RUNNING, AgentLifecycleState.DRAINING, AgentLifecycleState.TERMINATED},
    AgentLifecycleState.RUNNING: {
        AgentLifecycleState.WAITING,
        AgentLifecycleState.COMPLETED,
        AgentLifecycleState.FAILED,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.DRAINING,
    },
    AgentLifecycleState.WAITING: {
        AgentLifecycleState.RUNNING,
        AgentLifecycleState.FAILED,
        AgentLifecycleState.CANCELLED,
    },
    AgentLifecycleState.DRAINING: {AgentLifecycleState.COMPLETED, AgentLifecycleState.TERMINATED},
    AgentLifecycleState.COMPLETED: {AgentLifecycleState.READY, AgentLifecycleState.TERMINATED},
    AgentLifecycleState.FAILED: {AgentLifecycleState.READY, AgentLifecycleState.TERMINATED},
    AgentLifecycleState.CANCELLED: {AgentLifecycleState.READY, AgentLifecycleState.TERMINATED},
    AgentLifecycleState.TERMINATED: set(),
}


def can_transition(current: AgentLifecycleState, target: AgentLifecycleState) -> bool:
    """Validate whether an agent state transition is legal."""
    if current == target:
        return True
    return target in VALID_LIFECYCLE_TRANSITIONS.get(current, set())


class AgentLifecycleManager:
    """Manages lifecycle state transitions for agents according to formal rules (Spec 9)."""

    def __init__(self) -> None:
        self._states: dict[str, AgentLifecycleState] = {}

    def get_state(self, agent_id: str) -> AgentLifecycleState:
        return self._states.get(agent_id, AgentLifecycleState.CREATED)

    def transition(self, agent_id: str, target: AgentLifecycleState) -> bool:
        curr = self.get_state(agent_id)
        if not can_transition(curr, target):
            raise ValueError(f"Illegal lifecycle transition for agent {agent_id}: {curr.value} -> {target.value}")
        self._states[agent_id] = target
        return True

