"""Domain models, state machines, and data schemas for Task 90 Reliability Intelligence.

Covers:
- Reliability signal models with multi-horizon early warning states
- Component-aware baselines, trend directions, and rate-of-change models
- Failure forecasts, causal driver analyses, and predicted blast-radius impacts
- Prevention candidates, reversibility classifications, and counterfactual comparisons
- Structured decision explanations (problem, evidence, impact, options, why, verification)
- Prediction-vs-reality calibration, false positives, false negatives, and scorecards
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_ri_id(prefix: str = "ri") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ==============================================================================
# 1. ENUMS & TAXONOMIES
# ==============================================================================

class ReliabilitySignalType(str, Enum):
    """17 canonical reliability signal categories defined in Task 90."""

    RESOURCE_PRESSURE = "RESOURCE_PRESSURE"
    LATENCY_DEGRADATION = "LATENCY_DEGRADATION"
    ERROR_RATE_RISE = "ERROR_RATE_RISE"
    CRASH_LOOP = "CRASH_LOOP"
    NETWORK_INSTABILITY = "NETWORK_INSTABILITY"
    QUEUE_SATURATION = "QUEUE_SATURATION"
    CONNECTION_EXHAUSTION = "CONNECTION_EXHAUSTION"
    MEMORY_EXHAUSTION = "MEMORY_EXHAUSTION"
    CPU_EXHAUSTION = "CPU_EXHAUSTION"
    DISK_EXHAUSTION = "DISK_EXHAUSTION"
    DEPENDENCY_DEGRADATION = "DEPENDENCY_DEGRADATION"
    TOOL_DEGRADATION = "TOOL_DEGRADATION"
    WORKFLOW_DEGRADATION = "WORKFLOW_DEGRADATION"
    RECOVERY_DEGRADATION = "RECOVERY_DEGRADATION"
    VERIFICATION_DEGRADATION = "VERIFICATION_DEGRADATION"
    SECURITY_ANOMALY = "SECURITY_ANOMALY"
    PROTOCOL_INSTABILITY = "PROTOCOL_INSTABILITY"


class EarlyWarningState(str, Enum):
    """6-tier early-warning progression ladder with deterministic transitions."""

    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    IMMINENT = "IMMINENT"


class TrendDirection(str, Enum):
    """Empirical trend orientation derived from real telemetry samples."""

    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    OSCILLATING = "OSCILLATING"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


class ForecastHorizon(str, Enum):
    """Time-horizon classification supported by Task 74 prediction model."""

    IMMEDIATE = "IMMEDIATE"  # 0 to 2 minutes
    SHORT = "SHORT"          # 2 to 15 minutes
    MEDIUM = "MEDIUM"        # 15 to 60 minutes
    LONG = "LONG"            # 1 to 24 hours


class ReversibilityLevel(str, Enum):
    """Reversibility declaration of a candidate preventive intervention."""

    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"
    UNKNOWN = "UNKNOWN"


class AutonomyAdaptationLevel(str, Enum):
    """Dynamic operational autonomy states adapted according to system stability."""

    FULL = "FULL"
    CAUTIOUS = "CAUTIOUS"
    RESTRICTED = "RESTRICTED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
    STOPPED = "STOPPED"


class PreventionActionType(str, Enum):
    """Canonical preventive actions executable before failure occurs."""

    REDUCE_CONCURRENCY = "REDUCE_CONCURRENCY"
    RELEASE_RESOURCE = "RELEASE_RESOURCE"
    RECONNECT = "RECONNECT"
    REFRESH_POOL = "REFRESH_POOL"
    PAUSE_LOW_PRIORITY_WORK = "PAUSE_LOW_PRIORITY_WORK"
    DEGRADE_CAPABILITY = "DEGRADE_CAPABILITY"
    MOVE_WORK = "MOVE_WORK"
    RESCHEDULE = "RESCHEDULE"
    PREWARM_RESOURCE = "PREWARM_RESOURCE"
    RESTART_COMPONENT = "RESTART_COMPONENT"
    FAILOVER = "FAILOVER"
    THROTTLE = "THROTTLE"
    PAUSE_WORKFLOW = "PAUSE_WORKFLOW"
    ESCALATE = "ESCALATE"
    NO_ACTION = "NO_ACTION"  # Mandatory counterfactual baseline


class PreventionStatus(str, Enum):
    """Lifecycle states of a preventive intervention."""

    PENDING = "PENDING"
    SIMULATING = "SIMULATING"
    SIMULATED = "SIMULATED"
    RECOMMENDED = "RECOMMENDED"
    AUTHORIZING = "AUTHORIZING"
    AUTHORIZED = "AUTHORIZED"
    BUDGETED = "BUDGETED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ESCALATED = "ESCALATED"


# ==============================================================================
# 2. BASELINE & TELEMETRY MODELS
# ==============================================================================

class MetricBaseline(BaseModel):
    """Component-aware, time-bounded historical metric baseline."""

    model_config = ConfigDict(extra="ignore")

    component: str
    metric_name: str
    baseline_value: float
    unit: str = ""
    sample_count: int = 0
    window_duration_seconds: float = 300.0
    freshness_seconds: float = 0.0
    confidence: float = 1.0
    stdev: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    timestamp: datetime = Field(default_factory=_now_utc)


class MetricRateOfChange(BaseModel):
    """Calculated slope, acceleration, and threshold crossing projection."""

    metric_name: str
    current_value: float
    rate_per_minute: float
    acceleration: float = 0.0
    threshold_value: Optional[float] = None
    estimated_time_to_threshold_minutes: Optional[float] = None
    uncertainty_interval_minutes: Optional[str] = None  # e.g. "5-15 min"
    confidence: float = 0.8
    trend: TrendDirection = TrendDirection.UNKNOWN


# ==============================================================================
# 3. RELIABILITY SIGNAL MODEL (Section 4)
# ==============================================================================

class ReliabilitySignal(BaseModel):
    """Typed reliability signal embodying precursor telemetry anomalies."""

    model_config = ConfigDict(extra="ignore")

    signal_id: str = Field(default_factory=lambda: generate_ri_id("sig"))
    signal_type: ReliabilitySignalType
    component: str
    timestamp: datetime = Field(default_factory=_now_utc)
    severity: str = "P2"  # P0, P1, P2, P3
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    trend: TrendDirection = TrendDirection.UNKNOWN
    baseline: Optional[float] = None
    current_value: float = 0.0
    forecast: Optional[str] = None
    forecast_horizon: ForecastHorizon = ForecastHorizon.SHORT
    metric_name: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = Field(default_factory=lambda: generate_ri_id("corr"))
    trace_id: Optional[str] = None
    source: str = "observability_fabric"
    model_version: str = "1.0.0"
    state: EarlyWarningState = EarlyWarningState.WATCH


# ==============================================================================
# 4. FORECAST, CAUSAL DRIVER & RISK MODELS
# ==============================================================================

class FailureForecast(BaseModel):
    """Failure projection synthesized via Task 74 forecasting bridge."""

    forecast_id: str = Field(default_factory=lambda: generate_ri_id("fc"))
    target_component: str
    failure_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    time_horizon: ForecastHorizon = ForecastHorizon.SHORT
    estimated_time_to_failure_minutes: Optional[float] = None
    uncertainty_interval: Optional[str] = "unknown"
    prevention_window_minutes: Optional[float] = None
    confidence: float = 0.8
    evidence: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)


class CausalDriverAnalysis(BaseModel):
    """Causal factors identified via Task 73 causal root-cause modeling."""

    driver_id: str = Field(default_factory=lambda: generate_ri_id("cause"))
    primary_trigger: str
    underlying_condition: str
    mechanism: str
    causal_strength: float = Field(default=0.7, ge=0.0, le=1.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    contributing_factors: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class PredictedImpact(BaseModel):
    """Systemic blast-radius and cascade exposure via Task 75 risk propagation."""

    blast_radius_score: float = Field(default=0.2, ge=0.0, le=1.0)
    affected_components: List[str] = Field(default_factory=list)
    affected_workflows: List[str] = Field(default_factory=list)
    affected_resources: List[str] = Field(default_factory=list)
    security_impact: str = "NONE"  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    user_impact: str = "LOW"
    operational_impact: str = "MINIMAL"


# ==============================================================================
# 5. PREVENTION CANDIDATES & COUNTERFACTUAL COMPARISONS
# ==============================================================================

class PreventionCandidate(BaseModel):
    """Evaluated preventive action candidate."""

    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(default_factory=lambda: generate_ri_id("cand"))
    action_type: PreventionActionType
    target_component: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    is_no_action: bool = False
    reversibility: ReversibilityLevel = ReversibilityLevel.REVERSIBLE
    minimum_intervention_rank: int = 1

    # Simulated Metrics (from Task 89)
    predicted_benefit: float = 0.8        # e.g. avoided failure likelihood
    intervention_risk: float = 0.1        # risk of causing disruption
    intervention_cost: Dict[str, float] = Field(default_factory=dict) # CPU, memory delta
    simulated_blast_radius: float = 0.1
    estimated_duration_seconds: float = 1.0
    confidence: float = 0.8

    # Scoring
    net_prevention_value: float = 0.0     # benefit - cost - risk
    is_recommended: bool = False


class CounterfactualComparison(BaseModel):
    """Explicit side-by-side evaluation of candidates against NO_ACTION baseline."""

    comparison_id: str = Field(default_factory=lambda: generate_ri_id("cmp"))
    baseline_no_action: PreventionCandidate
    evaluated_candidates: List[PreventionCandidate] = Field(default_factory=list)
    selected_candidate: Optional[PreventionCandidate] = None
    selection_rationale: str = ""
    minimum_intervention_applied: bool = True


# ==============================================================================
# 6. DECISION EXPLANATION (Section 47)
# ==============================================================================

class DecisionExplanation(BaseModel):
    """Concise, structured explanation for operator inspection (zero private CoT)."""

    problem: str
    evidence: List[str]
    expected_impact: str
    options: List[str]
    selected_action: str
    why: str
    confidence: float
    uncertainty: str
    verification: str


# ==============================================================================
# 7. PREDICTIVE INCIDENT MODEL (Section 16)
# ==============================================================================

class PredictiveIncident(BaseModel):
    """Authoritative proactive reliability incident container."""

    model_config = ConfigDict(extra="ignore")

    incident_id: str = Field(default_factory=lambda: generate_ri_id("pinc"))
    title: str
    target_component: str
    early_warning_state: EarlyWarningState = EarlyWarningState.WATCH
    signals: List[ReliabilitySignal] = Field(default_factory=list)
    forecast: Optional[FailureForecast] = None
    causal_drivers: Optional[CausalDriverAnalysis] = None
    predicted_impact: Optional[PredictedImpact] = None
    candidates: List[PreventionCandidate] = Field(default_factory=list)
    selected_prevention: Optional[PreventionCandidate] = None
    decision_explanation: Optional[DecisionExplanation] = None
    status: PreventionStatus = PreventionStatus.PENDING

    # Governance, Resource & Execution tracking
    autonomy_level: AutonomyAdaptationLevel = AutonomyAdaptationLevel.FULL
    authorization_granted: bool = False
    requires_approval: bool = False
    resource_budget_allocated: bool = False
    verification_passed: Optional[bool] = None
    stability_monitored: bool = False

    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


# ==============================================================================
# 8. CALIBRATION & METRICS (Sections 48–52)
# ==============================================================================

class ForecastCalibrationRecord(BaseModel):
    """Empirical calibration pairing predicted failure against actual reality."""

    calibration_id: str = Field(default_factory=lambda: generate_ri_id("calib"))
    incident_id: str
    predicted_failure: str
    actual_failure_occurred: bool
    predicted_horizon: str
    actual_horizon_seconds: Optional[float] = None
    predicted_confidence: float
    actual_correctness: float
    predicted_impact_score: float
    actual_impact_score: Optional[float] = None
    intervention_executed: bool = False
    timestamp: datetime = Field(default_factory=_now_utc)


class FalsePositiveRecord(BaseModel):
    """Tracks non-failures following warnings to tune sensitivity."""

    fp_id: str = Field(default_factory=lambda: generate_ri_id("fp"))
    incident_id: str
    signal_type: ReliabilitySignalType
    confidence: float
    evidence: Dict[str, Any]
    outcome: str = "NO_FAILURE_OBSERVED"
    intervention_occurred: bool
    recorded_at: datetime = Field(default_factory=_now_utc)


class FalseNegativeRecord(BaseModel):
    """Critical audit record for unforeseen failures that lacked early warning."""

    fn_id: str = Field(default_factory=lambda: generate_ri_id("fn"))
    failure_id: str
    component: str
    failure_description: str
    observable_precursor_present: bool = False
    precursor_detected: bool = False
    forecast_attempted: bool = False
    root_cause_of_miss: str = "MODEL_BLIND_SPOT"
    remediation_note: str = ""
    recorded_at: datetime = Field(default_factory=_now_utc)


class PreventionStrategyScorecard(BaseModel):
    """Per-strategy effectiveness scorecard."""

    strategy: PreventionActionType
    total_attempts: int = 0
    successes: int = 0
    failures: int = 0
    false_positives: int = 0
    verification_rate: float = 1.0
    average_duration_seconds: float = 1.0
    average_resource_cost: Dict[str, float] = Field(default_factory=dict)
    side_effects_detected: int = 0
    health_status: str = "HEALTHY"
