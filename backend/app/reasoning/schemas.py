"""Domain schemas for Kairo Autonomous Reasoning & Deliberation Engine (Task 71).

Enforces:
- Structured deliberation without private chain-of-thought exposure
- Explicit 15-state reasoning lifecycle
- Independent epistemic constructs: Reasoning != Truth != Confidence != Consensus
- Bounded problem decomposition (DAG depth <= 3)
- Competing hypotheses, counterarguments, and falsification criteria
- Evidence evaluation, conflict detection, and source independence
- Dynamic assumption-dependency invalidation cascades
- Cognitive effort & resource budgeting
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReasoningState(StrEnum):
    """Explicit 15-state reasoning lifecycle."""

    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    DECOMPOSING = "DECOMPOSING"
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    EVIDENCE_EVALUATION = "EVIDENCE_EVALUATION"
    DELIBERATING = "DELIBERATING"
    CONCLUDING = "CONCLUDING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"

    # Terminal / Interrupted / Blocked
    BLOCKED = "BLOCKED"
    UNCERTAIN = "UNCERTAIN"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"


class ReasoningDepth(StrEnum):
    """Reasoning effort tier determining iteration and compute limits."""

    QUICK = "QUICK"  # Simple queries, minimal branching
    STANDARD = "STANDARD"  # Normal multi-step diagnostic/analytical analysis
    DEEP = "DEEP"  # Complex problems with extensive alternative comparison
    CRITICAL = "CRITICAL"  # High-impact/high-risk decisions requiring strict verification


class HypothesisStatus(StrEnum):
    """Lifecycle status of candidate hypotheses."""

    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    WEAKLY_SUPPORTED = "WEAKLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    DISPROVEN = "DISPROVEN"
    UNRESOLVED = "UNRESOLVED"
    VERIFIED = "VERIFIED"
    SUPERSEDED = "SUPERSEDED"


class AssumptionStatus(StrEnum):
    """Validation state of tracked assumptions."""

    UNVERIFIED = "UNVERIFIED"
    VALIDATED = "VALIDATED"
    INVALIDATED = "INVALIDATED"


class ConclusionStatus(StrEnum):
    """Lifecycle status of synthesized conclusions."""

    CANDIDATE = "CANDIDATE"
    PROVISIONAL = "PROVISIONAL"
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"


class ReasoningConfidence(StrEnum):
    """Calibrated confidence tier (strictly decoupled from truth)."""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class UncertaintyType(StrEnum):
    """Epistemic classification of knowledge under reasoning."""

    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING = "CONFLICTING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EscalationType(StrEnum):
    """Escalation trigger when autonomous deliberation reaches bounds."""

    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    NEEDS_TOOL = "NEEDS_TOOL"
    NEEDS_SPECIALIST_AGENT = "NEEDS_SPECIALIST_AGENT"


class GraphEdgeType(StrEnum):
    """Typed relationships in the reasoning DAG graph."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"
    INVALIDATES = "INVALIDATES"
    VERIFIES = "VERIFIES"
    LEADS_TO = "LEADS_TO"


class ReasoningBudget(BaseModel):
    """Resource bounds for a reasoning session."""

    max_depth: int = Field(default=3, ge=1, le=5)
    max_subproblems: int = Field(default=8, ge=1, le=20)
    max_hypotheses: int = Field(default=6, ge=1, le=15)
    max_iterations: int = Field(default=12, ge=1, le=50)
    max_latency_sec: float = Field(default=60.0, ge=1.0)
    max_tool_calls: int = Field(default=5, ge=0)
    tool_calls_used: int = Field(default=0, ge=0)
    iterations_used: int = Field(default=0, ge=0)


class SubProblem(BaseModel):
    """Structured decomposition unit."""

    subproblem_id: str = Field(default_factory=lambda: f"subp-{uuid4().hex[:8]}")
    parent_id: str | None = None
    question: str
    objective: str = ""
    status: str = "PENDING"  # PENDING, IN_PROGRESS, RESOLVED, BLOCKED
    priority: str = "NORMAL"
    depth_level: int = Field(default=1, ge=1, le=5)
    dependencies: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    conclusion: str | None = None
    confidence: ReasoningConfidence = ReasoningConfidence.MEDIUM


class ReasoningEvidence(BaseModel):
    """Structured empirical observation with provenance and trust."""

    evidence_id: str = Field(default_factory=lambda: f"evd-{uuid4().hex[:8]}")
    source_type: str = "observation"  # memory, event, observation, tool_result, database, log, document, research, agent, user
    source_id: str = Field(default_factory=lambda: f"src-{uuid4().hex[:6]}")
    content_summary: str
    raw_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    trust_level: str = (
        "KNOWN_SOURCE"  # VERIFIED, TRUSTED, KNOWN_SOURCE, UNVERIFIED, EXTERNAL, SUSPICIOUS, QUARANTINED
    )
    reliability: float = Field(default=0.8, ge=0.0, le=1.0)
    relevance: float = Field(default=0.8, ge=0.0, le=1.0)
    independence_group: str = Field(
        default="default",
        description="Shared ID across agents copying the same source to avoid false consensus",
    )
    verification_state: str = "UNVERIFIED"
    is_conflict: bool = False
    conflicting_evidence_ids: list[str] = Field(default_factory=list)


class ReasoningHypothesis(BaseModel):
    """Candidate explanation or solution with falsification criteria."""

    hypothesis_id: str = Field(default_factory=lambda: f"hyp-{uuid4().hex[:8]}")
    subproblem_id: str | None = None
    description: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(
        default_factory=list, description="Empirical conditions that would disprove this hypothesis"
    )
    counterarguments: list[str] = Field(default_factory=list)
    confidence: ReasoningConfidence = ReasoningConfidence.MEDIUM
    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    source: str = "internal"
    created_at: datetime = Field(default_factory=utc_now)


class ReasoningAssumption(BaseModel):
    """Explicitly tracked assumption with dependent conclusion cascade."""

    assumption_id: str = Field(default_factory=lambda: f"asm-{uuid4().hex[:8]}")
    description: str
    status: AssumptionStatus = AssumptionStatus.UNVERIFIED
    dependent_conclusion_ids: list[str] = Field(default_factory=list)
    validation_source: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ReasoningAlternative(BaseModel):
    """Comparative alternative option with tradeoff attributes."""

    alternative_id: str = Field(default_factory=lambda: f"alt-{uuid4().hex[:8]}")
    title: str
    description: str = ""
    risk_score: float = Field(default=0.3, ge=0.0, le=1.0)
    cost_score: float = Field(default=0.2, ge=0.0, le=1.0)
    time_estimate_sec: int = Field(default=60, ge=1)
    reversibility: float = Field(default=0.8, ge=0.0, le=1.0)
    expected_impact: float = Field(default=0.7, ge=0.0, le=1.0)
    confidence: ReasoningConfidence = ReasoningConfidence.MEDIUM
    dependencies: list[str] = Field(default_factory=list)


class ReasoningConclusion(BaseModel):
    """Synthesized conclusion with explicit provenance and uncertainty."""

    conclusion_id: str = Field(default_factory=lambda: f"concl-{uuid4().hex[:8]}")
    subproblem_id: str | None = None
    summary: str
    status: ConclusionStatus = ConclusionStatus.PROVISIONAL
    confidence: ReasoningConfidence = ReasoningConfidence.MEDIUM
    uncertainty_state: UncertaintyType = UncertaintyType.KNOWN
    supporting_hypothesis_ids: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)
    counterarguments_addressed: list[str] = Field(default_factory=list)
    falsification_tested: bool = False
    verification_id: str | None = None
    is_verified: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class ReasoningGraphNode(BaseModel):
    """A node in the reasoning DAG graph."""

    node_id: str
    node_type: str  # question, subproblem, hypothesis, evidence, assumption, conclusion, alternative
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReasoningGraphEdge(BaseModel):
    """A typed edge in the reasoning DAG graph."""

    source_id: str
    target_id: str
    edge_type: GraphEdgeType
    weight: float = 1.0


class ReasoningGraph(BaseModel):
    """Complete reasoning graph representation."""

    nodes: list[ReasoningGraphNode] = Field(default_factory=list)
    edges: list[ReasoningGraphEdge] = Field(default_factory=list)


class ReasoningExplanation(BaseModel):
    """User-safe concise explanation (strictly no private chain-of-thought)."""

    conclusion_summary: str
    confidence: ReasoningConfidence
    uncertainty_state: UncertaintyType
    supporting_reasons: list[str] = Field(default_factory=list)
    counterarguments_addressed: list[str] = Field(default_factory=list)
    assumptions_made: list[str] = Field(default_factory=list)
    remaining_uncertainty: str = ""


class ReasoningTraceEvent(BaseModel):
    """Auditable milestone event during deliberation."""

    event_id: str = Field(default_factory=lambda: f"revt-{uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=utc_now)
    phase: ReasoningState
    action: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReasoningRequest(BaseModel):
    """Payload to initiate a structured reasoning session."""

    tenant_id: str = "default"
    workspace_id: str = "default"
    user_id: str = "default_user"
    session_id: str | None = None
    task_id: str | None = None
    goal_id: str | None = None
    mission_id: str | None = None
    attention_id: str | None = None
    question: str
    objective: str = ""
    intent: str = ""
    depth: ReasoningDepth = ReasoningDepth.STANDARD
    context_refs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    required_confidence: ReasoningConfidence = ReasoningConfidence.MEDIUM
    risk_level: str = "MEDIUM"
    budget: ReasoningBudget = Field(default_factory=ReasoningBudget)


class ReasoningSession(BaseModel):
    """Complete in-flight or completed reasoning session state."""

    reasoning_id: str = Field(default_factory=lambda: f"rsn-{uuid4().hex[:12]}")
    tenant_id: str = "default"
    workspace_id: str = "default"
    user_id: str = "default_user"
    session_id: str | None = None
    task_id: str | None = None
    goal_id: str | None = None
    mission_id: str | None = None
    attention_id: str | None = None
    question: str
    objective: str = ""
    intent: str = ""
    depth: ReasoningDepth = ReasoningDepth.STANDARD
    current_state: ReasoningState = ReasoningState.CREATED
    confidence: ReasoningConfidence = ReasoningConfidence.MEDIUM
    uncertainty_state: UncertaintyType = UncertaintyType.UNCERTAIN

    # Structured deliberation artifacts
    subproblems: list[SubProblem] = Field(default_factory=list)
    hypotheses: list[ReasoningHypothesis] = Field(default_factory=list)
    evidence: list[ReasoningEvidence] = Field(default_factory=list)
    assumptions: list[ReasoningAssumption] = Field(default_factory=list)
    alternatives: list[ReasoningAlternative] = Field(default_factory=list)
    conclusions: list[ReasoningConclusion] = Field(default_factory=list)
    graph: ReasoningGraph = Field(default_factory=ReasoningGraph)

    # Budgets & Trace
    budget: ReasoningBudget = Field(default_factory=ReasoningBudget)
    trace_events: list[ReasoningTraceEvent] = Field(default_factory=list)
    explanation: ReasoningExplanation | None = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class ReasoningHealthMetrics(BaseModel):
    """Operational telemetry and health metrics for reasoning engine."""

    active_reasoning_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    average_reasoning_latency_sec: float = 0.0
    total_hypotheses_generated: int = 0
    total_evidence_evaluated: int = 0
    contradictions_detected: int = 0
    assumptions_invalidated: int = 0
    verification_pass_rate: float = 1.0
    average_confidence: str = "MEDIUM"
    resource_utilization_pct: float = 0.0
