"""Pydantic schemas and domain models for Collective Intelligence & Swarm Reasoning Engine (Task 64)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SwarmTopology(str, enum.Enum):
    """Coordination patterns for collective agent swarms."""

    STAR = "STAR"
    PIPELINE = "PIPELINE"
    DEBATE = "DEBATE"
    HIERARCHICAL = "HIERARCHICAL"
    PEER_TO_PEER = "PEER_TO_PEER"


class SwarmStatus(str, enum.Enum):
    """Lifecycle states of a swarm session."""

    INITIALIZING = "INITIALIZING"
    DECOMPOSING = "DECOMPOSING"
    RUNNING = "RUNNING"
    ANALYZING = "ANALYZING"
    REVIEWING = "REVIEWING"
    DEBATING = "DEBATING"
    SYNTHESIZING = "SYNTHESIZING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentHealthState(str, enum.Enum):
    """Operational health states for specialized agents (UNKNOWN != HEALTHY)."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    DISABLED = "DISABLED"


class TaskStatus(str, enum.Enum):
    """Status of tasks in swarm DAG."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYABLE = "RETRYABLE"


class DisagreementType(str, enum.Enum):
    """10-class taxonomy of agent disagreements."""

    FACTUAL = "FACTUAL"
    EVIDENCE = "EVIDENCE"
    CAUSAL = "CAUSAL"
    ASSUMPTION = "ASSUMPTION"
    OBJECTIVE = "OBJECTIVE"
    SCOPE = "SCOPE"
    TEMPORAL = "TEMPORAL"
    MODEL = "MODEL"
    INTERPRETATION = "INTERPRETATION"
    PREFERENCE = "PREFERENCE"


class DebateStatus(str, enum.Enum):
    """Status of a controlled debate session."""

    IN_PROGRESS = "IN_PROGRESS"
    CONVERGED = "CONVERGED"
    STALEMATE = "STALEMATE"
    RESOLVED = "RESOLVED"
    CONCLUDED = "CONCLUDED"
    MAX_ROUNDS_REACHED = "MAX_ROUNDS_REACHED"


class ConsensusOutcome(str, enum.Enum):
    """Evidence-weighted consensus classifications."""

    CONSENSUS = "CONSENSUS"
    QUALIFIED_CONSENSUS = "QUALIFIED_CONSENSUS"
    MINORITY_DISAGREEMENT = "MINORITY_DISAGREEMENT"
    UNRESOLVED = "UNRESOLVED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EpistemicType(str, enum.Enum):
    """Strict taxonomy for agent assertions (OBSERVATION != CLAIM != INFERENCE)."""

    OBSERVATION = "OBSERVATION"
    EVIDENCE = "EVIDENCE"
    CLAIM = "CLAIM"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    PREDICTION = "PREDICTION"
    RECOMMENDATION = "RECOMMENDATION"


class EvidenceStrength(str, enum.Enum):
    """Empirical strength levels of cited evidence."""

    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"
    UNVERIFIED = "UNVERIFIED"


class CollectiveObjective(BaseModel):
    """Shared objective driving collective swarm reasoning."""

    model_config = ConfigDict(extra="ignore")

    objective_id: str = Field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:10]}")
    goal: str = Field(..., description="Target reasoning goal or problem statement")
    context: dict[str, Any] = Field(default_factory=dict, description="Domain context and background data")
    constraints: list[str] = Field(default_factory=list, description="Hard constraints and boundaries")
    success_criteria: list[str] = Field(default_factory=list, description="Verification criteria for success")
    deadline: datetime | None = None
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH, CRITICAL
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    required_evidence: list[str] = Field(default_factory=list)
    tenant_id: str = "default"
    origin_subsystem: str = "user"  # user, planner, decision, incident_response, optimization, research
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)


class SwarmAgentSpec(BaseModel):
    """Specialized agent specification in swarm."""

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(default_factory=lambda: f"ag_{uuid.uuid4().hex[:8]}")
    name: str
    role: str  # ARCHITECT, SECURITY_ANALYST, CRITIC, ANALYST, RESEARCHER, etc.
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    model_profile: str = "default"
    tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    trust_level: float = 0.8
    specialization: str = "general"
    health: AgentHealthState = AgentHealthState.HEALTHY
    cost_profile: float = 1.0
    latency_profile_ms: float = 500.0
    can_execute_production: bool = False
    version: str = "1.0.0"
    provenance: dict[str, Any] = Field(default_factory=dict)


class SwarmTaskNode(BaseModel):
    """Node in Swarm Task DAG."""

    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    title: str
    description: str = ""
    role_needed: str
    assigned_agent_id: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    is_critical_path: bool = False
    result_id: str | None = None
    retry_count: int = 0
    max_retries: int = 2
    execution_time_seconds: float = 0.0
    error: str | None = None


class TaskDAG(BaseModel):
    """Directed Acyclic Graph representing decomposed tasks."""

    model_config = ConfigDict(extra="ignore")

    dag_id: str = Field(default_factory=lambda: f"dag_{uuid.uuid4().hex[:8]}")
    objective_id: str
    tasks: list[SwarmTaskNode] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    dependencies_map: dict[str, list[str]] = Field(default_factory=dict)


class AgentAssertion(BaseModel):
    """Structured atomic assertion produced by an agent."""

    model_config = ConfigDict(extra="ignore")

    assertion_id: str = Field(default_factory=lambda: f"ast_{uuid.uuid4().hex[:8]}")
    text: str
    epistemic_type: EpistemicType = EpistemicType.CLAIM
    confidence: float = 0.75
    evidence_refs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    source_lineage: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Output produced by a specialist agent for a specific task."""

    model_config = ConfigDict(extra="ignore")

    result_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    agent_id: str
    task_id: str
    role: str
    answer: str
    claims: list[AgentAssertion] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    limitations: list[str] = Field(default_factory=list)
    tool_usage: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_now_utc)
    provenance: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"


class PeerReview(BaseModel):
    """Independent review of an agent's result by another agent."""

    model_config = ConfigDict(extra="ignore")

    review_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:8]}")
    reviewer_agent_id: str
    reviewer_role: str
    target_result_id: str
    target_agent_id: str = ""
    correctness_score: float = 0.8
    issues: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    counterarguments: list[str] = Field(default_factory=list)
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: float = 0.8
    recommendation: str = "ENDORSE"  # ENDORSE, QUALIFIED_ENDORSE, CONTEST, REJECT
    is_blind: bool = True
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now_utc)


class DisagreementRecord(BaseModel):
    """Identified and classified disagreement between agents."""

    model_config = ConfigDict(extra="ignore")

    disagreement_id: str = Field(default_factory=lambda: f"dis_{uuid.uuid4().hex[:8]}")
    category: DisagreementType
    issue: str
    involved_agent_ids: list[str] = Field(default_factory=list)
    positions: dict[str, str] = Field(default_factory=dict)  # agent_id -> position text
    root_cause_explanation: str = ""
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    status: str = "DETECTED"  # DETECTED, DEBATING, RESOLVED, UNRESOLVED
    resolution: str | None = None
    created_at: datetime = Field(default_factory=_now_utc)


class DebateTurn(BaseModel):
    """Single argument turn in a controlled debate."""

    model_config = ConfigDict(extra="ignore")

    turn_id: str = Field(default_factory=lambda: f"trn_{uuid.uuid4().hex[:8]}")
    round_number: int
    agent_id: str
    role: str
    statement: str
    counter_to_agent_id: str | None = None
    evidence_cited: list[str] = Field(default_factory=list)
    confidence: float = 0.8


class DebateRound(BaseModel):
    """One round of structured debate."""

    model_config = ConfigDict(extra="ignore")

    round_number: int
    turns: list[DebateTurn] = Field(default_factory=list)
    summary: str = ""
    consensus_delta: float = 0.0


class DebateSession(BaseModel):
    """Controlled multi-agent debate session with round and timeout boundaries."""

    model_config = ConfigDict(extra="ignore")

    debate_id: str = Field(default_factory=lambda: f"dbt_{uuid.uuid4().hex[:8]}")
    topic: str
    participants: list[str] = Field(default_factory=list)  # agent_ids
    rounds: list[DebateRound] = Field(default_factory=list)
    status: DebateStatus = DebateStatus.IN_PROGRESS
    max_rounds: int = 3
    outcome: str = ""
    start_time: datetime = Field(default_factory=_now_utc)
    end_time: datetime | None = None


class MinorityReport(BaseModel):
    """Preserved dissenting perspective when consensus is not unanimous."""

    model_config = ConfigDict(extra="ignore")

    minority_id: str = Field(default_factory=lambda: f"min_{uuid.uuid4().hex[:8]}")
    dissenting_agent_id: str
    dissenting_role: str
    position: str
    evidence: list[str] = Field(default_factory=list)
    reasoning: str
    confidence: float = 0.75
    failure_scenario_conditions: list[str] = Field(default_factory=list)
    divergence_from_majority: str = ""


class ConsensusResult(BaseModel):
    """Evidence-weighted consensus determination."""

    model_config = ConfigDict(extra="ignore")

    outcome: ConsensusOutcome = ConsensusOutcome.CONSENSUS
    consensus_score: float = 0.85
    majority_opinion: str
    supporting_agents: list[str] = Field(default_factory=list)
    dissenting_agents: list[str] = Field(default_factory=list)
    confidence: float = 0.80
    rationale: str = ""
    is_evidence_backed: bool = True


class CollectiveResult(BaseModel):
    """Synthesized final result produced by collective intelligence engine."""

    model_config = ConfigDict(extra="ignore")

    result_id: str = Field(default_factory=lambda: f"col_{uuid.uuid4().hex[:10]}")
    objective_id: str
    swarm_id: str
    goal: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    agent_perspectives: dict[str, str] = Field(default_factory=dict)
    consensus: ConsensusResult | None = None
    minority_positions: list[MinorityReport] = Field(default_factory=list)
    disagreements: list[DisagreementRecord] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    verification_status: str = "UNVERIFIED"  # UNVERIFIED, VERIFIED, FAILED
    affected_systems: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=_now_utc)


class SwarmSession(BaseModel):
    """Active swarm reasoning session tracking state, agents, and artifacts."""

    model_config = ConfigDict(extra="ignore")

    swarm_id: str = Field(default_factory=lambda: f"swm_{uuid.uuid4().hex[:10]}")
    objective: CollectiveObjective
    topology: SwarmTopology = SwarmTopology.STAR
    status: SwarmStatus = SwarmStatus.INITIALIZING
    agents: list[SwarmAgentSpec] = Field(default_factory=list)
    task_dag: TaskDAG | None = None
    results: list[AgentResult] = Field(default_factory=list)
    reviews: list[PeerReview] = Field(default_factory=list)
    debates: list[DebateSession] = Field(default_factory=list)
    disagreements: list[DisagreementRecord] = Field(default_factory=list)
    minority_reports: list[MinorityReport] = Field(default_factory=list)
    consensus: ConsensusResult | None = None
    final_result: CollectiveResult | None = None
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class SwarmCreateRequest(BaseModel):
    """Request payload to create and launch a collective swarm reasoning session."""

    goal: str
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    topology: SwarmTopology = SwarmTopology.STAR
    roles: list[str] | None = None
    priority: str = "NORMAL"
    risk_level: str = "MEDIUM"
    tenant_id: str = "default"
    max_rounds: int = 3
    timeout_seconds: int = 300


class SwarmActionRequest(BaseModel):
    """Request payload for pausing, resuming, or cancelling a swarm session."""

    action: str  # pause, resume, cancel
    actor: str = "operator"
    reason: str = ""
