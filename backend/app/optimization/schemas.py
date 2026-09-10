"""Pydantic schemas and domain models for Continuous Self-Optimization & Adaptive Control Engine (Task 62)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ObjectiveDirection(str, Enum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FeedbackTrustLevel(str, Enum):
    VERIFIED_SYSTEM = "VERIFIED_SYSTEM"
    VERIFIED_EXTERNAL = "VERIFIED_EXTERNAL"
    TRUSTED_HUMAN = "TRUSTED_HUMAN"
    OPERATIONAL_OBSERVATION = "OPERATIONAL_OBSERVATION"
    MODEL_JUDGMENT = "MODEL_JUDGMENT"
    UNVERIFIED_EXTERNAL = "UNVERIFIED_EXTERNAL"


class ExperimentStatus(str, Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"


class ChangeSetStatus(str, Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    REVERTED = "REVERTED"
    FAILED = "FAILED"


class RolloutState(str, Enum):
    PENDING = "PENDING"
    CANARY_10 = "CANARY_10"
    CANARY_50 = "CANARY_50"
    FULL_ROLLOUT = "FULL_ROLLOUT"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class DriftType(str, Enum):
    DATA_DRIFT = "DATA_DRIFT"
    MODEL_DRIFT = "MODEL_DRIFT"
    SYSTEM_DRIFT = "SYSTEM_DRIFT"
    BASELINE_DRIFT = "BASELINE_DRIFT"
    METRIC_DRIFT = "METRIC_DRIFT"
    CONFIG_DRIFT = "CONFIG_DRIFT"


class RecommendationType(str, Enum):
    CHANGE_MODEL_ROUTING = "CHANGE_MODEL_ROUTING"
    ADJUST_RESOURCE_ALLOCATION = "ADJUST_RESOURCE_ALLOCATION"
    ADJUST_TIMEOUT = "ADJUST_TIMEOUT"
    ADJUST_BATCHING = "ADJUST_BATCHING"
    ADJUST_CACHE = "ADJUST_CACHE"
    ADJUST_NON_CRITICAL_THRESHOLD = "ADJUST_NON_CRITICAL_THRESHOLD"
    CHANGE_TASK_PRIORITY = "CHANGE_TASK_PRIORITY"
    CHANGE_PLANNING_WEIGHT = "CHANGE_PLANNING_WEIGHT"
    CHANGE_MODEL_SELECTION = "CHANGE_MODEL_SELECTION"


# Metric Models
class MetricMeasurement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    measurement_id: str = Field(default_factory=lambda: f"meas_{uuid.uuid4().hex[:8]}")
    metric_name: str
    value: float
    timestamp: datetime = Field(default_factory=_now_utc)
    source: str = "telemetry"
    scope: str = "global"
    tags: dict[str, str] = Field(default_factory=dict)


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    metric_name: str
    description: str
    unit: str
    direction: ObjectiveDirection = ObjectiveDirection.MINIMIZE
    min_samples_required: int = 5
    target_value: float | None = None
    sla_threshold: float | None = None


class MetricAggregation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    metric_name: str
    sample_count: int
    mean: float
    min_value: float
    max_value: float
    p50: float
    p95: float
    p99: float
    has_sufficient_data: bool = True
    freshness_seconds: float = 0.0


# Objectives & Constraints
class OptimizationObjective(BaseModel):
    model_config = ConfigDict(extra="ignore")

    objective_id: str = Field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:8]}")
    name: str
    metric_name: str
    direction: ObjectiveDirection = ObjectiveDirection.MINIMIZE
    weight: float = 1.0
    target_range: tuple[float, float] | None = None


class HardConstraint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    constraint_id: str = Field(default_factory=lambda: f"cst_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    is_immutable: bool = True
    enforcement_scope: str = "global"
    max_allowed_value: float | None = None
    min_allowed_value: float | None = None


class SoftPreference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preference_id: str = Field(default_factory=lambda: f"prf_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    weight: float = 0.5


# Bounded Adjustable Parameters
class AdjustableParameter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    parameter_name: str
    description: str
    minimum: float
    maximum: float
    default_value: float
    current_value: float
    max_step_change: float
    requires_approval: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    scope: str = "runtime"


# Baseline Model
class OptimizationBaseline(BaseModel):
    model_config = ConfigDict(extra="ignore")

    baseline_id: str = Field(default_factory=lambda: f"bsl_{uuid.uuid4().hex[:8]}")
    metric_name: str
    baseline_value: float
    std_dev: float = 0.0
    sample_size: int = 0
    version: int = 1
    environment: str = "production"
    is_quarantined: bool = False
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


# Feedback Signal
class FeedbackSignal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signal_id: str = Field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:8]}")
    source: str
    trust_level: FeedbackTrustLevel = FeedbackTrustLevel.OPERATIONAL_OBSERVATION
    content: str
    numeric_feedback: float | None = None
    metric_name: str | None = None
    timestamp: datetime = Field(default_factory=_now_utc)
    provenance: dict[str, Any] = Field(default_factory=dict)


# Gap & Recommendation
class OptimizationGap(BaseModel):
    model_config = ConfigDict(extra="ignore")

    gap_id: str = Field(default_factory=lambda: f"gap_{uuid.uuid4().hex[:8]}")
    metric_name: str
    current_value: float
    target_value: float
    gap_delta: float
    gap_percentage: float
    likely_contributors: list[str] = Field(default_factory=list)
    confidence: float = 0.85
    urgency: str = "NORMAL"


class OptimizationRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recommendation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:8]}")
    recommendation_type: RecommendationType
    title: str
    description: str
    target_parameter: str
    current_value: float
    proposed_value: float
    expected_benefit: str
    expected_cost: str = "NEGLIGIBLE"
    risk: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    is_simulated: bool = False
    simulation_notes: str = ""
    rollback_strategy: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.90


# Change Sets & Canaries
class ChangeSet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    change_set_id: str = Field(default_factory=lambda: f"cs_{uuid.uuid4().hex[:8]}")
    version: int = 1
    target_parameter: str
    before_state: float
    after_state: float
    diff: dict[str, Any] = Field(default_factory=dict)
    reason: str
    risk: RiskLevel = RiskLevel.LOW
    status: ChangeSetStatus = ChangeSetStatus.DRAFT
    approval_id: str | None = None
    approver: str | None = None
    rollback_strategy: str
    created_at: datetime = Field(default_factory=_now_utc)


class CanaryDeployment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    canary_id: str = Field(default_factory=lambda: f"cnr_{uuid.uuid4().hex[:8]}")
    change_set_id: str
    rollout_state: RolloutState = RolloutState.PENDING
    traffic_percentage: float = 0.0
    blast_radius_scope: str = "canary_partition"
    is_verified: bool = False
    failure_threshold_reached: bool = False
    started_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class RollbackPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rollback_id: str = Field(default_factory=lambda: f"rbk_{uuid.uuid4().hex[:8]}")
    change_set_id: str
    target_parameter: str
    restoration_value: float
    is_executed: bool = False
    is_verified: bool = False
    reconciled_state: dict[str, Any] = Field(default_factory=dict)


# Experiments
class ExperimentVariant(BaseModel):
    model_config = ConfigDict(extra="ignore")

    variant_id: str
    name: str
    parameter_overrides: dict[str, float] = Field(default_factory=dict)
    sample_allocation_pct: float = 50.0


class Experiment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    hypothesis: str
    target_metrics: list[str] = Field(default_factory=list)
    control_parameters: dict[str, float] = Field(default_factory=dict)
    variants: list[ExperimentVariant] = Field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    safety_gates: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)


# Drift & Calibration
class DriftRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drift_id: str = Field(default_factory=lambda: f"dft_{uuid.uuid4().hex[:8]}")
    drift_type: DriftType
    scope: str
    severity: RiskLevel = RiskLevel.MEDIUM
    baseline_value: float
    observed_value: float
    divergence_score: float
    evidence: str
    detected_at: datetime = Field(default_factory=_now_utc)


class CalibrationRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    record_id: str = Field(default_factory=lambda: f"cal_{uuid.uuid4().hex[:8]}")
    recommendation_id: str
    predicted_improvement_pct: float
    actual_improvement_pct: float
    prediction_error: float
    confidence_score: float
    is_overconfident: bool = False
    recorded_at: datetime = Field(default_factory=_now_utc)


# Master Evaluation & Outcome
class OptimizationEvaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evaluation_id: str = Field(default_factory=lambda: f"eval_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=_now_utc)
    metrics_summary: list[MetricAggregation] = Field(default_factory=list)
    detected_gaps: list[OptimizationGap] = Field(default_factory=list)
    generated_recommendations: list[OptimizationRecommendation] = Field(default_factory=list)
    drift_alerts: list[DriftRecord] = Field(default_factory=list)
    is_healthy: bool = True


class OptimizationOutcome(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: f"out_{uuid.uuid4().hex[:8]}")
    change_set_id: str
    actual_metrics_before: dict[str, float] = Field(default_factory=dict)
    actual_metrics_after: dict[str, float] = Field(default_factory=dict)
    is_beneficial: bool = True
    verified_at: datetime = Field(default_factory=_now_utc)


# API Requests & Responses
class IngestMeasurementRequest(BaseModel):
    metric_name: str
    value: float
    source: str = "telemetry"
    scope: str = "global"
    tags: dict[str, str] = Field(default_factory=dict)


class EvaluateOptimizationRequest(BaseModel):
    scope: str = "global"
    include_simulation: bool = True


class ApproveRecommendationRequest(BaseModel):
    recommendation_id: str
    approver: str = "SYSTEM_ADMIN"
    notes: str = "Authorized bounded adaptive parameter change"


class CreateExperimentRequest(BaseModel):
    hypothesis: str
    target_metrics: list[str]
    control_parameters: dict[str, float]
    variants: list[ExperimentVariant]
    safety_gates: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)


class CanaryDeployRequest(BaseModel):
    change_set_id: str
    traffic_percentage: float = 10.0


class RollbackChangeSetRequest(BaseModel):
    change_set_id: str
    reason: str = "Operational degradation observed during canary"
    actor: str = "OPERATOR"


class KillSwitchRequest(BaseModel):
    engage: bool = True
    reason: str = "Operational anomaly emergency freeze"
    actor: str = "SECURITY_LEAD"
