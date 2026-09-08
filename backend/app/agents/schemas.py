"""Pydantic schemas for Multi-Agent Orchestration specs, plans, context, and results."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agents.state import AgentTaskStatus, AgentType, EvidenceType


class AgentDefinition(BaseModel):
    """Specification of an agent role, allowed tools, and capabilities."""

    name: str
    agent_type: AgentType | str
    description: str
    allowed_tools: list[str] = Field(default_factory=list)
    model_capability: str = "general"
    max_execution_time_seconds: int = 300
    max_tool_calls: int = 20


class AgentTaskSpec(BaseModel):
    """Specification of a single sub-agent task in an orchestration plan."""

    task_id: str = Field(..., description="Unique identifier for this task in the plan")
    agent_type: AgentType | str = Field(..., description="Target specialist agent type")
    objective: str = Field(..., description="Clear, bounded goal for the specialist")
    dependencies: list[str] = Field(
        default_factory=list, description="IDs of tasks that must finish before this task"
    )
    input_context: dict[str, Any] = Field(
        default_factory=dict, description="Scoped parameters and initial data"
    )


class AgentPlan(BaseModel):
    """Validated Directed Acyclic Graph (DAG) plan of tasks to be orchestrated."""

    tasks: list[AgentTaskSpec] = Field(default_factory=list)


class AgentEvidence(BaseModel):
    """Structured piece of evidence classified as OBSERVED, INFERRED, or UNKNOWN."""

    type: EvidenceType | str = EvidenceType.OBSERVED
    statement: str
    source: str | None = None
    timestamp: datetime | None = None


class AgentCitation(BaseModel):
    """Verified reference/source for research-based facts."""

    id: int
    title: str
    url: str
    snippet: str | None = None


class AgentResult(BaseModel):
    """Structured outcome returned by a specialist agent upon task completion."""

    task_id: str
    agent_type: str
    status: AgentTaskStatus | str = AgentTaskStatus.COMPLETED
    summary: str
    evidence: list[AgentEvidence] = Field(default_factory=list)
    structured_output: dict[str, Any] = Field(default_factory=dict)
    citations: list[AgentCitation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    tool_calls_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentContext(BaseModel):
    """Scoped, isolated execution context passed to an individual specialist agent."""

    task_id: str
    parent_task_id: str | None = None
    user_id: str = "default_user"
    session_id: str | None = None
    agent_type: AgentType | str
    bounded_input: str
    dependencies_results: dict[str, AgentResult] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    max_tool_calls: int = 20
    timeout_seconds: int = 300


class AgentTaskRead(BaseModel):
    """Database representation of an agent task."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    parent_task_id: str | None = None
    user_id: str
    session_id: str | None = None
    agent_type: str
    status: str
    objective: str
    dependencies: list[str] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result_summary: str | None = None


class AgentTaskCancelResponse(BaseModel):
    """Response payload when canceling an agent task."""

    task_id: str
    status: str
    cancelled: bool


class AgentStreamingEvent(BaseModel):
    """Safe, non-reasoning progress event emitted during multi-agent execution."""

    event_type: str  # agent_started, agent_progress, agent_completed, agent_failed, approval_required, synthesis_started
    agent_type: str
    task_id: str | None = None
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
