"""Domain models, enums, and state machines for Task 96:
Autonomous Multi-Agent Collaboration, Delegation, Supervision & Swarm Orchestration Engine.

Strictly enforces:
- AGENT != AUTHORITY
- AGENT ROLE != PERMISSION
- PARENT SCOPE >= CHILD SCOPE
- DELEGATION != PRIVILEGE ESCALATION
- UNVALIDATED != AUTHORITATIVE
- EMERGENCY STOP ALWAYS WINS
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_hex(prefix: str, length: int = 10) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


# ==============================================================================
# Phase 2: Agent Roles
# ==============================================================================

class AgentRole(str, Enum):
    """Explicit specialized roles in Kairo swarm orchestration (Phase 2)."""
    RESEARCHER = "RESEARCHER"
    ANALYST = "ANALYST"
    CODER = "CODER"
    DEBUGGER = "DEBUGGER"
    PLANNER = "PLANNER"
    VALIDATOR = "VALIDATOR"
    REVIEWER = "REVIEWER"
    SIMULATOR = "SIMULATOR"
    MONITOR = "MONITOR"
    EXECUTOR = "EXECUTOR"
    RECOVERY_AGENT = "RECOVERY_AGENT"
    SYNTHESIZER = "SYNTHESIZER"


# ==============================================================================
# Phase 3: Agent Lifecycle State Machine
# ==============================================================================

class AgentLifecycleState(str, Enum):
    """Rigid operational lifecycle states of an autonomous agent instance (Phase 3)."""
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED = "BLOCKED"
    RECOVERING = "RECOVERING"
    TERMINATED = "TERMINATED"
    EXPIRED = "EXPIRED"


# Legal State Transitions
ALLOWED_AGENT_TRANSITIONS: dict[AgentLifecycleState, set[AgentLifecycleState]] = {
    AgentLifecycleState.CREATED: {
        AgentLifecycleState.QUEUED,
        AgentLifecycleState.INITIALIZING,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.QUEUED: {
        AgentLifecycleState.INITIALIZING,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.EXPIRED,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.INITIALIZING: {
        AgentLifecycleState.RUNNING,
        AgentLifecycleState.BLOCKED,
        AgentLifecycleState.FAILED,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.RUNNING: {
        AgentLifecycleState.WAITING,
        AgentLifecycleState.PAUSED,
        AgentLifecycleState.COMPLETED,
        AgentLifecycleState.FAILED,
        AgentLifecycleState.TIMED_OUT,
        AgentLifecycleState.BLOCKED,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.WAITING: {
        AgentLifecycleState.RUNNING,
        AgentLifecycleState.TIMED_OUT,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.PAUSED: {
        AgentLifecycleState.RUNNING,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.BLOCKED: {
        AgentLifecycleState.RUNNING,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.TERMINATED,
        AgentLifecycleState.FAILED,
    },
    AgentLifecycleState.FAILED: {
        AgentLifecycleState.RECOVERING,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.RECOVERING: {
        AgentLifecycleState.RUNNING,
        AgentLifecycleState.FAILED,
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.TIMED_OUT: {
        AgentLifecycleState.TERMINATED,
    },
    AgentLifecycleState.COMPLETED: set(),
    AgentLifecycleState.CANCELLED: set(),
    AgentLifecycleState.TERMINATED: set(),
    AgentLifecycleState.EXPIRED: set(),
}


# ==============================================================================
# Phase 1: Strongly Typed Agent Identity
# ==============================================================================

class LifecycleTransition(BaseModel):
    """Immutable record of an agent lifecycle state transition."""
    from_state: AgentLifecycleState
    to_state: AgentLifecycleState
    timestamp: datetime = Field(default_factory=_now_utc)
    reason: str = ""


class AgentIdentity(BaseModel):
    """Strongly typed, scoped agent identity preventing impersonation (Phase 1)."""
    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(default_factory=lambda: _uuid_hex("ag"))
    role: AgentRole
    parent_agent_id: str | None = None
    session_id: str
    task_id: str | None = None

    capability_scope: list[str] = Field(default_factory=list)
    context_scope: str = "PRIVATE_AGENT_CONTEXT"  # PRIVATE_AGENT_CONTEXT, SHARED_TASK_CONTEXT, SHARED_EVIDENCE
    resource_scope: dict[str, Any] = Field(default_factory=dict)

    lifecycle_state: AgentLifecycleState = AgentLifecycleState.CREATED
    lifecycle_reason: str = ""
    trust_score: float = 0.85
    history: list[LifecycleTransition] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=_now_utc)
    expires_at: datetime = Field(default_factory=lambda: _now_utc() + timedelta(minutes=30))
    updated_at: datetime = Field(default_factory=_now_utc)

    correlation_id: str | None = None
    trace_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.lifecycle_state in (
            AgentLifecycleState.INITIALIZING,
            AgentLifecycleState.RUNNING,
            AgentLifecycleState.WAITING,
            AgentLifecycleState.PAUSED,
            AgentLifecycleState.RECOVERING,
        )

    @property
    def is_terminal(self) -> bool:
        return self.lifecycle_state in (
            AgentLifecycleState.COMPLETED,
            AgentLifecycleState.FAILED,
            AgentLifecycleState.CANCELLED,
            AgentLifecycleState.TIMED_OUT,
            AgentLifecycleState.TERMINATED,
            AgentLifecycleState.EXPIRED,
        )

    def can_transition_to(self, target: AgentLifecycleState) -> bool:
        allowed = ALLOWED_AGENT_TRANSITIONS.get(self.lifecycle_state, set())
        return target in allowed

    def transition_to(self, target: AgentLifecycleState, reason: str = "") -> None:
        if not self.can_transition_to(target):
            raise ValueError(
                f"Illegal agent state transition from '{self.lifecycle_state.value}' to '{target.value}' for agent '{self.agent_id}'."
            )
        prev = self.lifecycle_state
        self.lifecycle_state = target
        self.lifecycle_reason = reason
        self.updated_at = _now_utc()
        self.history.append(
            LifecycleTransition(
                from_state=prev,
                to_state=target,
                timestamp=self.updated_at,
                reason=reason,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        data = self.model_dump()
        data["role"] = self.role.value
        data["lifecycle_state"] = self.lifecycle_state.value
        data["is_active"] = self.is_active
        data["is_terminal"] = self.is_terminal
        data["created_at"] = self.created_at.isoformat()
        data["expires_at"] = self.expires_at.isoformat() if self.expires_at else None
        data["updated_at"] = self.updated_at.isoformat()
        data["history"] = [
            {
                "from_state": h.from_state.value,
                "to_state": h.to_state.value,
                "timestamp": h.timestamp.isoformat(),
                "reason": h.reason,
            }
            for h in self.history
        ]
        return data


# ==============================================================================
# Phase 4 & 6: Agent Task & Dependency Graph
# ==============================================================================

class TaskDependencyState(str, Enum):
    READY = "READY"
    BLOCKED_BY_DEPENDENCY = "BLOCKED_BY_DEPENDENCY"
    RUNNABLE = "RUNNABLE"
    COMPLETED = "COMPLETED"


class AgentTask(BaseModel):
    """Bounded, executable unit of work delegated to an agent (Phase 4)."""
    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(default_factory=lambda: _uuid_hex("tsk"))
    parent_task_id: str | None = None
    root_task_id: str | None = None
    session_id: str

    objective: str
    role_needed: AgentRole
    assigned_agent_id: str | None = None
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH, CRITICAL

    dependencies: list[str] = Field(default_factory=list)  # list of prerequisite task_ids
    dependency_state: TaskDependencyState = TaskDependencyState.READY

    required_capabilities: list[str] = Field(default_factory=list)
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    security_scope: list[str] = Field(default_factory=list)
    governance_scope: dict[str, Any] = Field(default_factory=dict)

    expected_output_schema: dict[str, Any] = Field(default_factory=dict)
    validation_policy: str = "STRICT_SCHEMA_AND_EVIDENCE"
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"max_retries": 2, "current_retries": 0})
    cancellation_policy: str = "PROPAGATE_TO_CHILDREN"

    deadline: datetime | None = None
    created_at: datetime = Field(default_factory=_now_utc)
    completed_at: datetime | None = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED


# ==============================================================================
# Phase 17 & 18: Typed Communication & Shared Blackboard
# ==============================================================================

class MessageType(str, Enum):
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"
    TASK_UPDATE = "TASK_UPDATE"
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"
    EVIDENCE = "EVIDENCE"
    RESULT = "RESULT"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    CANCELLATION = "CANCELLATION"
    DEPENDENCY_UPDATE = "DEPENDENCY_UPDATE"
    ESCALATION = "ESCALATION"


class AgentMessage(BaseModel):
    """Typed, provenance-tracked inter-agent message (Phase 17)."""
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(default_factory=lambda: _uuid_hex("msg"))
    session_id: str
    sender_id: str
    recipient_id: str
    task_id: str | None = None
    message_type: MessageType

    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now_utc)


class BlackboardEntry(BaseModel):
    """Shared atomic fact or artifact on the bounded blackboard (Phase 18)."""
    model_config = ConfigDict(extra="ignore")

    entry_id: str = Field(default_factory=lambda: _uuid_hex("bb"))
    session_id: str
    key: str
    value: Any
    author_agent_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    is_validated: bool = False
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)

    @property
    def content(self) -> Any:
        return self.value


# ==============================================================================
# Phase 19, 20, 22: Result Contract, Validation, Consensus & Synthesis
# ==============================================================================

class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    UNVALIDATED = "UNVALIDATED"
    INVALID = "INVALID"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class ConsensusClassification(str, Enum):
    CONSISTENT = "CONSISTENT"
    PARTIALLY_CONSISTENT = "PARTIALLY_CONSISTENT"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"


# ==============================================================================
# Phase 24 & 25: Supervision & Stall Detection
# ==============================================================================

class StallState(str, Enum):
    HEALTHY = "HEALTHY"
    SLOW = "SLOW"
    STALLED = "STALLED"
    FAILING = "FAILING"
    RUNAWAY = "RUNAWAY"


# ==============================================================================
# Phase 14: Delegation Tree Safety Limits
# ==============================================================================

class DelegationLimits(BaseModel):
    """Hard safety limits preventing runaway recursion and amplification (Phase 14)."""
    max_depth: int = 4
    max_children_per_agent: int = 5
    max_total_agents: int = 15
    max_tasks: int = 30
    max_runtime_seconds: float = 600.0
    max_memory_mb: int = 4096
