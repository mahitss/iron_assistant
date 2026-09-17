"""Domain models, enumerations, and canonical entities for Task 104:
KAIRO Autonomous Continuous Evaluation, Benchmarking, Regression & Improvement Governance Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ExecutionMode(str, Enum):
    """Execution environment mode distinguishing real vs simulated vs replay."""

    REAL = "REAL"
    SHADOW = "SHADOW"
    SIMULATED = "SIMULATED"
    REPLAY = "REPLAY"
    SYNTHETIC = "SYNTHETIC"


class ReplayReproducibility(str, Enum):
    """Classification of replay determinism and reproducibility."""

    EXACT_REPLAY = "EXACT_REPLAY"
    REPRODUCIBLE_REPLAY = "REPRODUCIBLE_REPLAY"
    APPROXIMATE_REPLAY = "APPROXIMATE_REPLAY"
    NON_REPRODUCIBLE = "NON_REPRODUCIBLE"


class ScenarioClass(str, Enum):
    """Evaluation scenario taxonomy classes."""

    DETERMINISTIC = "deterministic"
    REPLAY = "replay"
    SIMULATION = "simulation"
    SYNTHETIC = "synthetic"
    HISTORICAL = "historical"
    PRODUCTION_DERIVED = "production_derived"
    ADVERSARIAL = "adversarial"
    CHAOS_FAULT_INJECTION = "chaos_fault_injection"
    SHADOW = "shadow"
    HOLDOUT = "holdout"


class RunStatus(str, Enum):
    """Lifecycle status of an evaluation run."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"
    SUPERSEDED = "SUPERSEDED"


class GateStatus(str, Enum):
    """Outcome of an evaluation gate evaluation."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReviewStatus(str, Enum):
    """Status of human or governance review."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUESTED_CHANGES = "REQUESTED_CHANGES"
    EXPIRED = "EXPIRED"


class RegressionCategory(str, Enum):
    """Categories of detected system regressions."""

    FUNCTIONAL = "FUNCTIONAL"
    QUALITY = "QUALITY"
    SAFETY = "SAFETY"
    SECURITY = "SECURITY"
    RELIABILITY = "RELIABILITY"
    PERFORMANCE = "PERFORMANCE"
    RESOURCE = "RESOURCE"
    CALIBRATION = "CALIBRATION"
    MEMORY = "MEMORY"
    CONTEXT = "CONTEXT"
    AUTONOMY = "AUTONOMY"
    COMPATIBILITY = "COMPATIBILITY"
    OBSERVABILITY = "OBSERVABILITY"


class RegressionSeverity(str, Enum):
    """Severity of detected regressions aligned with governance risk ratings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BaselineType(str, Enum):
    """Type of baseline used for comparison."""

    PREVIOUS_PRODUCTION = "previous_production"
    PREVIOUS_CAPABILITY = "previous_capability"
    PREVIOUS_EVALUATION = "previous_evaluation"
    GOLDEN = "golden"
    HISTORICAL = "historical"
    NO_ACTION = "no_action"
    HEURISTIC = "heuristic"
    SIMULATION = "simulation"


class MetricType(str, Enum):
    """Typed evaluation metrics across all sub-systems."""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    FALSE_NEGATIVE_RATE = "false_negative_rate"
    CALIBRATION_ERROR = "calibration_error"
    BRIER_SCORE = "brier_score"
    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    THROUGHPUT = "throughput"
    SUCCESS_RATE = "success_rate"
    FAILURE_RATE = "failure_rate"
    RECOVERY_RATE = "recovery_rate"
    VERIFICATION_RATE = "verification_rate"
    UNKNOWN_OUTCOME_RATE = "unknown_outcome_rate"
    REGRESSION_RATE = "regression_rate"
    RESOURCE_COST = "resource_cost"
    TOKEN_COST = "token_cost"
    MEMORY_RETRIEVAL_UTILITY = "memory_retrieval_utility"
    FACTUAL_CORRECTNESS = "factual_correctness"
    CONTEXT_RELEVANCE = "context_relevance"
    MISSION_COMPLETION = "mission_completion"
    MISSION_REGRESSION = "mission_regression"
    SITUATION_DETECTION_QUALITY = "situation_detection_quality"
    DECISION_OUTCOME_QUALITY = "decision_outcome_quality"
    PREDICTION_ERROR = "prediction_error"
    FORECAST_CALIBRATION = "forecast_calibration"
    CAPABILITY_READINESS_ACCURACY = "capability_readiness_accuracy"
    SELF_MODEL_CALIBRATION = "self_model_calibration"
    AGENT_AGREEMENT = "agent_agreement"
    AGENT_DISAGREEMENT = "agent_disagreement"
    COORDINATION_OVERHEAD = "coordination_overhead"
    CONTROL_CYCLE_DURATION = "control_cycle_duration"
    CONTROL_CYCLE_FAILURE = "control_cycle_failure"
    SAFETY_VIOLATIONS = "safety_violations"
    POLICY_VIOLATIONS = "policy_violations"
    APPROVAL_BYPASS_ATTEMPTS = "approval_bypass_attempts"
    EMERGENCY_STOP_RESPONSE = "emergency_stop_response"
    ROLLBACK_SUCCESS = "rollback_success"
    RECOVERY_STABILITY = "recovery_stability"
    WORLD_STATE_DRIFT = "world_state_drift"
    EVIDENCE_COMPLETENESS = "evidence_completeness"


# -------------------------------------------------------------------------
# Core Domain Entities (Section 1)
# -------------------------------------------------------------------------

class EvaluationSuite(BaseModel):
    """Persistent evaluation suite configuration."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"suite_{uuid.uuid4().hex[:12]}")
    name: str
    description: str = ""
    scope: str = "SYSTEM"
    applicable_capabilities: list[str] = Field(default_factory=list)
    scenario_selection: list[str] = Field(default_factory=list)
    metric_definitions: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    safety_gates: list[str] = Field(default_factory=list)
    baseline_policy: str = "LATEST_GOLDEN"
    required_evidence: list[str] = Field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.REAL
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 300.0
    concurrency_limit: int = 4
    sampling_rate: float = 1.0
    holdout_policy: str = "EXCLUDE_UNLESS_RELEASE"
    review_required: bool = False
    version: str = "1.0.0"
    status: str = "ACTIVE"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationScenario(BaseModel):
    """Structured evaluation scenario representation."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"scen_{uuid.uuid4().hex[:12]}")
    name: str
    scenario_class: ScenarioClass = ScenarioClass.DETERMINISTIC
    category: str = "general"
    description: str = ""
    initial_world_state: dict[str, Any] = Field(default_factory=dict)
    relevant_self_state: dict[str, Any] = Field(default_factory=dict)
    objective: str = ""
    available_capabilities: list[str] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    user_intent: str = ""
    environmental_conditions: dict[str, Any] = Field(default_factory=dict)
    expected_observations: list[str] = Field(default_factory=list)
    expected_behavior: str = ""
    expected_postconditions: list[str] = Field(default_factory=list)
    forbidden_behavior: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    time_budget_ms: float = 30000.0
    adversarial_conditions: dict[str, Any] = Field(default_factory=dict)
    expected_uncertainty: float = 0.0
    is_holdout: bool = False
    dataset_version: str = "v1.0.0"
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationCase(BaseModel):
    """Concrete evaluation case instance."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"case_{uuid.uuid4().hex[:12]}")
    scenario_id: str
    dataset_id: str
    dataset_version: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    expected_output: Any = None
    evaluation_criteria: dict[str, Any] = Field(default_factory=dict)
    is_golden: bool = False
    is_edge_case: bool = False
    is_adversarial: bool = False
    contamination_detected: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationDataset(BaseModel):
    """Dataset container for evaluation cases."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"ds_{uuid.uuid4().hex[:12]}")
    name: str
    domain: str = "general"
    source_type: str = "SYNTHETIC"
    creation_reason: str = "baseline_verification"
    is_immutable: bool = True
    contamination_detected: bool = False
    case_count: int = 0
    golden_case_count: int = 0
    edge_case_count: int = 0
    adversarial_count: int = 0
    failure_corpus_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationDatasetVersion(BaseModel):
    """Immutable versioned snapshot of an evaluation dataset."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"dsv_{uuid.uuid4().hex[:12]}")
    dataset_id: str
    version: str = "v1.0.0"
    fingerprint: str = ""
    case_ids: list[str] = Field(default_factory=list)
    is_frozen: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationFixture(BaseModel):
    """Pre-configured mock or synthetic fixture for evaluation scenarios."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"fix_{uuid.uuid4().hex[:12]}")
    name: str
    fixture_type: str = "mock"
    state_payload: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationBaseline(BaseModel):
    """Immutable baseline metrics against which candidate runs are evaluated."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"base_{uuid.uuid4().hex[:12]}")
    name: str
    baseline_type: BaselineType = BaselineType.GOLDEN
    version: str = "1.0.0"
    suite_id: str = ""
    dataset_version: str = "v1.0.0"
    capability_versions: dict[str, str] = Field(default_factory=dict)
    model_version: str = "default"
    environment: str = "staging"
    metrics: dict[str, float] = Field(default_factory=dict)
    is_frozen: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationRun(BaseModel):
    """Lifecycle record of a continuous evaluation or benchmark run."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    suite_id: str
    suite_name: str
    dataset_version: str = "v1.0.0"
    baseline_id: Optional[str] = None
    candidate_version: str = "dev"
    capability_versions: dict[str, str] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.REAL
    status: RunStatus = RunStatus.CREATED
    pass_rate: float = 0.0
    security_pass_rate: float = 1.0
    safety_pass_rate: float = 1.0
    quality_score: float = 0.0
    latency_p95_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    total_tokens: int = 0
    cases_total: int = 0
    cases_passed: int = 0
    cases_failed: int = 0
    cases_inconclusive: int = 0
    cases_blocked: int = 0
    is_resumable: bool = True
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:8]}")
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    configuration_snapshot: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunCase(BaseModel):
    """Result of an individual scenario case within an evaluation run."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"runcase_{uuid.uuid4().hex[:12]}")
    run_id: str
    case_id: str
    scenario_id: str
    scenario_name: str
    execution_mode: ExecutionMode = ExecutionMode.REAL
    execution_success: bool = False
    outcome_success: bool = False
    passed: bool = False
    score: float = 0.0
    uncertainty: float = 0.0
    status: str = "COMPLETED"
    duration_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    actual_output: Any = None
    failures: list[str] = Field(default_factory=list)
    trace_events: list[dict[str, Any]] = Field(default_factory=list)
    replay_reproducibility: Optional[ReplayReproducibility] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MetricMeasurement(BaseModel):
    """Specific quantitative or qualitative measurement for a run or comparison."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"meas_{uuid.uuid4().hex[:12]}")
    run_id: str
    metric_name: str
    metric_type: MetricType
    value: float
    unit: str = "ratio"
    sample_size: int = 1
    confidence_interval_low: Optional[float] = None
    confidence_interval_high: Optional[float] = None
    variance: Optional[float] = None
    status: GateStatus = GateStatus.PASS
    threshold: Optional[float] = None
    direction: str = "HIGHER_IS_BETTER"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RegressionFinding(BaseModel):
    """Detected regression finding between candidate and baseline."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"regr_{uuid.uuid4().hex[:12]}")
    run_id: str
    baseline_id: str
    category: RegressionCategory
    severity: RegressionSeverity
    metric_name: str
    baseline_value: float
    candidate_value: float
    delta: float
    delta_percentage: float
    confidence: float = 0.95
    sample_size: int = 1
    is_statistically_significant: bool = True
    evidence_summary: str = ""
    is_blocking: bool = False
    affected_capabilities: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CalibrationFinding(BaseModel):
    """Findings regarding confidence calibration, overconfidence, and degradation."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"calib_{uuid.uuid4().hex[:12]}")
    run_id: str
    subsystem: str
    brier_score: float = 0.0
    expected_calibration_error: float = 0.0
    overconfidence_rate: float = 0.0
    underconfidence_rate: float = 0.0
    horizon_degradation_detected: bool = False
    sample_count: int = 0
    finding_summary: str = ""
    is_degraded: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SafetyFinding(BaseModel):
    """Findings regarding safety violations, prompt injection, and policy breaches."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"safe_{uuid.uuid4().hex[:12]}")
    run_id: str
    violation_type: str
    severity: RegressionSeverity = RegressionSeverity.CRITICAL
    details: str
    payload_sanitized: dict[str, Any] = Field(default_factory=dict)
    blocked: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImprovementProposal(BaseModel):
    """Governed proposal generated when weaknesses or regressions are detected."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:12]}")
    title: str
    problem_statement: str
    target_area: str
    affected_capabilities: list[str] = Field(default_factory=list)
    affected_metrics: list[str] = Field(default_factory=list)
    baseline_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    proposed_change: dict[str, Any] = Field(default_factory=dict)
    expected_benefit: str = ""
    expected_risks: list[str] = Field(default_factory=list)
    uncertainty: float = 0.0
    resource_estimate: dict[str, Any] = Field(default_factory=dict)
    rollback_plan: str = ""
    validation_plan: str = ""
    required_approvals: list[str] = Field(default_factory=list)
    affected_governance_policies: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    status: str = "PROPOSED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImprovementExperiment(BaseModel):
    """Controlled experiment testing an improvement proposal safely."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:12]}")
    proposal_id: str
    hypothesis: str
    control_baseline_id: str
    candidate_configuration: dict[str, Any] = Field(default_factory=dict)
    mode: ExecutionMode = ExecutionMode.SHADOW
    status: str = "PLANNED"
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    failure_criteria: dict[str, Any] = Field(default_factory=dict)
    safety_gates: list[str] = Field(default_factory=list)
    sample_size_target: int = 50
    current_sample_size: int = 0
    passed_safety_gates: bool = True
    stop_conditions_met: bool = False
    stop_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationEvidence(BaseModel):
    """Immutable evidence package supporting findings and proposals."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"evid_{uuid.uuid4().hex[:12]}")
    source_type: str
    source_id: str
    trace_events: list[dict[str, Any]] = Field(default_factory=list)
    world_state_snapshot: dict[str, Any] = Field(default_factory=dict)
    self_model_snapshot: dict[str, Any] = Field(default_factory=dict)
    decision_records: list[dict[str, Any]] = Field(default_factory=list)
    action_records: list[dict[str, Any]] = Field(default_factory=list)
    metrics_snapshot: dict[str, float] = Field(default_factory=dict)
    redacted_traces: list[dict[str, Any]] = Field(default_factory=list)
    environment_metadata: dict[str, Any] = Field(default_factory=dict)
    capability_fingerprint: str = ""
    is_sanitized: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationGate(BaseModel):
    """Evaluation gate evaluation record."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"gate_{uuid.uuid4().hex[:12]}")
    gate_name: str
    run_id: str
    status: GateStatus = GateStatus.INCONCLUSIVE
    threshold: Optional[float] = None
    measured_value: Optional[float] = None
    reason: str = ""
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationReview(BaseModel):
    """Human or governance authority review record for proposals and releases."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:12]}")
    proposal_id: str
    reviewer: str
    status: ReviewStatus = ReviewStatus.PENDING
    rationale: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationComparison(BaseModel):
    """Top-level release comparison record between candidate and baseline."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"comp_{uuid.uuid4().hex[:12]}")
    run_id: str
    baseline_id: str
    candidate_version: str
    baseline_version: str
    release_blocked: bool = False
    security_gate_passed: bool = True
    regressions_count: int = 0
    blocking_reasons: list[str] = Field(default_factory=list)
    deltas: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
