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
    version: str = "1.0.0"
    capabilities: list[str] = Field(default_factory=list)
    health_status: str = "HEALTHY"
    role: str = ""



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


# ==================================================
# Task 44 Collaboration & Collective Intelligence Schemas
# ==================================================

class CollaborationSessionCreate(BaseModel):
    goal: str
    user_id: str = "default_user"
    project_id: str = "default_project"
    scope: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"


class CollaborationSessionResponse(BaseModel):
    session_id: str
    goal: str
    user_id: str
    project_id: str
    status: str
    agents_count: int
    created_at: str


class AgentRegistrationRequest(BaseModel):
    name: str
    role: str
    capabilities: list[str] = Field(default_factory=list)
    model_profile: str = "default"
    permissions_scope: list[str] = Field(default_factory=list)
    tool_scope: list[str] = Field(default_factory=list)
    max_tokens: int = 50000
    max_cost: float = 1.0


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    role: str
    capabilities: list[str]
    status: str
    version: str
    health: str
    created_at: str


class ContractCreateRequest(BaseModel):
    agent_id: str
    parent_goal: str
    assigned_objective: str
    scope_resources: list[str] = Field(default_factory=list)
    scope_tools: list[str] = Field(default_factory=list)
    scope_data: list[str] = Field(default_factory=list)
    project_id: str = "default_project"
    token_budget: int = 10000
    tool_budget: int = 10
    cost_budget: float = 0.5


class ContractExpansionRequestSchema(BaseModel):
    contract_id: str
    reason: str
    requested_resources: list[str] = Field(default_factory=list)
    requested_tools: list[str] = Field(default_factory=list)
    requested_token_budget: int | None = None


class ContractResponse(BaseModel):
    contract_id: str
    agent_id: str
    assigned_objective: str
    status: str
    scope: dict[str, Any]
    budget: dict[str, Any]
    created_at: str


class DelegationRequest(BaseModel):
    session_id: str
    parent_goal: str
    subtask_id: str
    assigned_objective: str
    agent_role: str
    target_agent_id: str | None = None
    required_tools: list[str] = Field(default_factory=list)


class DelegationResponse(BaseModel):
    delegation_id: str
    contract_id: str
    subtask_id: str
    agent_id: str
    role: str
    status: str


class SendMessageRequest(BaseModel):
    sender_id: str
    recipient_id: str
    message_type: str
    payload: dict[str, Any]
    contract_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    priority: int = 0


class MessageResponse(BaseModel):
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: str
    status: str
    timestamp: str


class EvidenceCreateRequest(BaseModel):
    session_id: str
    producer_agent_id: str
    contract_id: str
    fact_type: str
    claim: str
    sources: list[str] = Field(default_factory=list)
    model_id: str = "default_model"
    is_verified: bool = False
    verification_source: str | None = None


class EvidenceResponse(BaseModel):
    evidence_id: str
    fact_type: str
    claim: str
    is_verified: bool
    producer_agent_id: str
    timestamp: str


class DisagreementCreateRequest(BaseModel):
    session_id: str
    subject: str
    claimant_a: str
    claim_a: str
    evidence_ids_a: list[str] = Field(default_factory=list)
    claimant_b: str
    claim_b: str
    evidence_ids_b: list[str] = Field(default_factory=list)
    severity: str = "MEDIUM"


class DisagreementResolveRequest(BaseModel):
    disagreement_id: str
    resolver_role: str = "SUPERVISOR"
    resolution_notes: str | None = None


class DisagreementResponse(BaseModel):
    disagreement_id: str
    subject: str
    severity: str
    status: str
    participants: list[str]
    resolution_summary: str | None = None


class ConsensusCheckRequest(BaseModel):
    topic: str
    evidence_ids: list[str] = Field(default_factory=list)


class ConsensusResponse(BaseModel):
    topic: str
    status: str
    claim_counts: dict[str, int]
    verified_claim: str | None
    total_evidence: int


class SynthesisRequest(BaseModel):
    session_id: str
    goal: str
    agent_result_ids: list[str] = Field(default_factory=list)


class SynthesisResponse(BaseModel):
    synthesis_id: str
    goal: str
    findings_count: int
    unresolved_conflicts_count: int
    recommendation: str
    is_verified: bool


class EmergencyStopRequest(BaseModel):
    session_id: str
    reason: str
    triggered_by: str = "SUPERVISOR"


class EmergencyStopResponse(BaseModel):
    session_id: str
    stopped: bool
    reason: str
    stopped_agents_count: int

