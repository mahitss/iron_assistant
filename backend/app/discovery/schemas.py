"""Domain schemas for Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine (Task 72).

Enforces:
- Epistemic boundaries: Hypothesis != Fact, Prediction != Observation, Experiment != Simulation
- Immutable pre-execution predictions
- 18-state discovery lifecycle and explicit experiment statuses
- 8 experiment classes with variable, control, and confounder tracking
- Multi-dimensional safety gating (SAFE to CRITICAL_RISK) with required rollback and cleanup
- Provenance tracking from research question through knowledge update
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class DiscoveryState(StrEnum):
    """Explicit 18-state scientific discovery lifecycle."""

    CREATED = "CREATED"
    QUESTION_FORMED = "QUESTION_FORMED"
    HYPOTHESIS_GENERATED = "HYPOTHESIS_GENERATED"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    READY = "READY"
    RUNNING = "RUNNING"
    OBSERVING = "OBSERVING"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    CONCLUDED = "CONCLUDED"
    KNOWLEDGE_UPDATE = "KNOWLEDGE_UPDATE"
    COMPLETED = "COMPLETED"

    # Branch / Interrupted states
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class ExperimentType(StrEnum):
    """8 supported experimental investigation classes."""

    OBSERVATIONAL = "OBSERVATIONAL"  # Passive metric/telemetry collection, no intervention
    DIAGNOSTIC = "DIAGNOSTIC"  # Comparing state before vs after an event
    CONTROLLED = "CONTROLLED"  # Controlled intervention with baseline in staging/isolated env
    AB = "AB"  # Direct split-variant comparison against control baseline
    SIMULATION = "SIMULATION"  # Synthetic model execution (strictly labeled SIMULATED)
    REPLAY = "REPLAY"  # Historical behavior reproduction
    RESEARCH = "RESEARCH"  # Document/literature synthesis
    USER_VALIDATION = "USER_VALIDATION"  # Human operator validation of assumption


class RiskLevel(StrEnum):
    """Safety classification determining autonomous execution vs approval requirements."""

    SAFE = "SAFE"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"


class ExperimentStatus(StrEnum):
    """Lifecycle status of a planned or running experiment."""

    PROPOSED = "PROPOSED"
    READY = "READY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INVALID = "INVALID"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class AnalysisOutcome(StrEnum):
    """Comparison outcome between pre-execution prediction and actual observations."""

    SUPPORTED = "SUPPORTED"
    WEAKLY_SUPPORTED = "WEAKLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    DISPROVEN = "DISPROVEN"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNEXPECTED = "UNEXPECTED"


class EnvironmentType(StrEnum):
    """Execution environment tiers for isolation."""

    SIMULATION = "SIMULATION"
    LOCAL = "LOCAL"
    TEST = "TEST"
    STAGING = "STAGING"
    CANARY = "CANARY"
    PRODUCTION = "PRODUCTION"


class GeneralizationScope(StrEnum):
    """Epistemic scope limit of an experimental conclusion."""

    LOCAL_ONLY = "LOCAL_ONLY"
    ENVIRONMENT_SPECIFIC = "ENVIRONMENT_SPECIFIC"
    CROSS_ENVIRONMENT = "CROSS_ENVIRONMENT"
    UNIVERSAL_CANDIDATE = "UNIVERSAL_CANDIDATE"


class EpistemicCategory(StrEnum):
    """Categorization of propositions strictly following epistemic principles."""

    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


class ResearchQuestion(BaseModel):
    """Structured question targeted at identifying and resolving unknowns."""

    question_id: str = Field(default_factory=lambda: f"qst-{uuid4().hex[:8]}")
    question: str
    scope: str = "system"
    importance: float = Field(default=0.8, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.7, ge=0.0, le=1.0)
    goal_alignment: str = ""
    decision_relevance: bool = True
    time_constraints: str | None = None
    required_evidence: list[str] = Field(default_factory=list)
    status: str = "OPEN"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryHypothesis(BaseModel):
    """Candidate explanation with explicit Popperian falsifiers."""

    hypothesis_id: str = Field(default_factory=lambda: f"dhyp-{uuid4().hex[:8]}")
    question_id: str | None = None
    description: str
    supporting_evidence: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    falsification_criteria: list[str] = Field(
        default_factory=list, description="Empirical observations that would refute this hypothesis"
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: str = "CANDIDATE"
    plausibility: float = Field(default=0.7, ge=0.0, le=1.0)
    testability: float = Field(default=0.8, ge=0.0, le=1.0)
    source: str = "autonomous_discovery"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreExecutionPrediction(BaseModel):
    """Immutable prediction recorded before experiment execution."""

    prediction_id: str = Field(default_factory=lambda: f"pred-{uuid4().hex[:8]}")
    experiment_id: str
    hypothesis_id: str
    expected_direction: str = "decrease"  # increase, decrease, constant, zero, distinct
    expected_range: str = ""  # e.g. "10% to 25% reduction in latency"
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    is_immutable: bool = True


class ExperimentObservation(BaseModel):
    """Empirically captured measurement or telemetry observation."""

    observation_id: str = Field(default_factory=lambda: f"obs-{uuid4().hex[:8]}")
    experiment_id: str
    source: str
    timestamp: datetime = Field(default_factory=utc_now)
    environment: EnvironmentType = EnvironmentType.STAGING
    measurement_metric: str
    value: float | str | dict[str, Any]
    unit: str = ""
    raw_reference: str = ""
    verification_state: str = "UNVERIFIED"
    is_simulation: bool = False


class RollbackPlan(BaseModel):
    """Deterministic rollback action for mutable experiments."""

    rollback_action: str = ""
    rollback_owner: str = "system"
    rollback_timeout_sec: int = Field(default=60, ge=1)
    rollback_verification: str = "check_baseline_metrics"


class CleanupPlan(BaseModel):
    """Deterministic resource and temporary artifact cleanup."""

    cleanup_action: str = ""
    temporary_resources: list[str] = Field(default_factory=list)
    cleanup_verified: bool = False


class ExperimentDesign(BaseModel):
    """Complete specification of an experimental investigation."""

    experiment_id: str = Field(default_factory=lambda: f"exp-{uuid4().hex[:8]}")
    discovery_id: str
    hypothesis_ids: list[str] = Field(default_factory=list)
    objective: str
    description: str = ""
    experiment_type: ExperimentType = ExperimentType.OBSERVATIONAL
    environment: EnvironmentType = EnvironmentType.STAGING
    scope: str = "isolated"

    # Variables
    independent_variables: dict[str, Any] = Field(default_factory=dict)
    dependent_variables: list[str] = Field(default_factory=list)
    control_variables: dict[str, Any] = Field(default_factory=dict)
    potential_confounders: list[str] = Field(default_factory=list)

    # Baseline & Criteria
    baseline: dict[str, Any] = Field(default_factory=dict)
    expected_result: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)
    falsification_criteria: list[str] = Field(default_factory=list)

    # Safety & Resource limits
    risk_level: RiskLevel = RiskLevel.LOW_RISK
    estimated_cost: float = Field(default=0.1, ge=0.0)
    estimated_duration_sec: int = Field(default=60, ge=1)
    expected_information_gain: float = Field(default=0.8, ge=0.0, le=1.0)
    required_tools: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    authorization_required: bool = False
    is_authorized: bool = False
    authorized_by: str | None = None

    # Safety rollback & cleanup
    rollback_plan: RollbackPlan = Field(default_factory=RollbackPlan)
    cleanup_plan: CleanupPlan = Field(default_factory=CleanupPlan)

    # Dependencies & Status
    dependencies: list[str] = Field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.PROPOSED

    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class ExperimentResult(BaseModel):
    """Analyzed outcome comparing pre-execution prediction to actual observations."""

    result_id: str = Field(default_factory=lambda: f"res-{uuid4().hex[:8]}")
    experiment_id: str
    outcome: AnalysisOutcome = AnalysisOutcome.SUPPORTED
    prediction_vs_observation_summary: str = ""
    effect_size: float = Field(default=0.0)
    unexpected_anomaly_detected: bool = False
    new_hypotheses: list[str] = Field(default_factory=list)
    new_hypotheses_suggested: list[str] = Field(default_factory=list)
    is_valid: bool = True
    invalidation_reason: str | None = None
    replication_status: str = "SINGLE_RUN"  # SINGLE_RUN, REPLICATED, REPLICATION_CONFLICT
    generalization_scope: GeneralizationScope = GeneralizationScope.ENVIRONMENT_SPECIFIC
    conclusions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class DiscoveryAuditEvent(BaseModel):
    """Auditable scientific event in the discovery lineage."""

    event_id: str = Field(default_factory=lambda: f"devt-{uuid4().hex[:8]}")
    discovery_id: str | None = None
    experiment_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: str
    description: str
    actor: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryRequest(BaseModel):
    """Payload to initiate a structured discovery and experimentation session."""

    tenant_id: str = "default"
    workspace_id: str = "default"
    user_id: str = "default_user"
    session_id: str | None = None
    goal_id: str | None = None
    mission_id: str | None = None
    task_id: str | None = None
    reasoning_id: str | None = None
    question: str
    objective: str = ""
    domain: str = "system"
    initial_hypotheses: list[Any] = Field(default_factory=list)
    max_experiments: int = Field(default=5, ge=1, le=20)
    risk_tolerance: RiskLevel = RiskLevel.MEDIUM_RISK


class DiscoverySession(BaseModel):
    """Complete aggregate state of an autonomous discovery session."""

    discovery_id: str = Field(default_factory=lambda: f"dsc-{uuid4().hex[:12]}")
    tenant_id: str = "default"
    workspace_id: str = "default"
    user_id: str = "default_user"
    session_id: str | None = None
    goal_id: str | None = None
    mission_id: str | None = None
    task_id: str | None = None
    reasoning_id: str | None = None

    question: str
    objective: str = ""
    domain: str = "system"
    status: DiscoveryState = DiscoveryState.CREATED
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    # Core scientific artifacts
    questions: list[ResearchQuestion] = Field(default_factory=list)
    hypotheses: list[DiscoveryHypothesis] = Field(default_factory=list)
    experiments: list[ExperimentDesign] = Field(default_factory=list)
    predictions: list[PreExecutionPrediction] = Field(default_factory=list)
    observations: list[ExperimentObservation] = Field(default_factory=list)
    results: list[ExperimentResult] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    audit_events: list[DiscoveryAuditEvent] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class DiscoveryHealthMetrics(BaseModel):
    """Operational telemetry and scientific discovery health metrics."""

    active_discoveries: int = 0
    completed_discoveries: int = 0
    failed_discoveries: int = 0
    active_experiments: int = 0
    queued_experiments: int = 0
    completed_experiments: int = 0
    failed_experiments: int = 0
    invalid_experiments: int = 0
    approval_wait_time: float = 0.0
    experiment_duration: float = 0.0
    information_gain: float = 0.0
    experiment_cost: float = 0.0
    experiment_risk: float = 0.0
    replication_rate: float = 0.0
    replication_conflict_rate: float = 0.0
    unexpected_result_rate: float = 0.0
    hypothesis_support_rate: float = 0.0
    hypothesis_disproof_rate: float = 0.0
    knowledge_promotion_rate: float = 0.0
    average_information_gain: float = 0.0
    safety_block_count: int = 0
