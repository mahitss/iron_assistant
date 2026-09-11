"""Pydantic Request and Response Schemas for Prediction REST API (Task 47)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==================================================
# Task 74 Domain Enums
# ==================================================

class ForecastState(str, Enum):
    """10-state lifecycle governing forecast validity and provenance (Spec 5)."""

    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    PUBLISHED = "PUBLISHED"
    MONITORING = "MONITORING"
    UPDATED = "UPDATED"
    VERIFIED_BY_OUTCOME = "VERIFIED_BY_OUTCOME"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"
    FAILED = "FAILED"


# Valid state transitions
VALID_FORECAST_TRANSITIONS: dict[ForecastState, set[ForecastState]] = {
    ForecastState.DRAFT: {ForecastState.GENERATED, ForecastState.FAILED},
    ForecastState.GENERATED: {ForecastState.PUBLISHED, ForecastState.FAILED, ForecastState.INVALIDATED},
    ForecastState.PUBLISHED: {ForecastState.MONITORING, ForecastState.UPDATED, ForecastState.SUPERSEDED, ForecastState.INVALIDATED, ForecastState.EXPIRED, ForecastState.VERIFIED_BY_OUTCOME},
    ForecastState.MONITORING: {ForecastState.UPDATED, ForecastState.VERIFIED_BY_OUTCOME, ForecastState.EXPIRED, ForecastState.INVALIDATED, ForecastState.SUPERSEDED},
    ForecastState.UPDATED: {ForecastState.MONITORING, ForecastState.VERIFIED_BY_OUTCOME, ForecastState.SUPERSEDED, ForecastState.INVALIDATED, ForecastState.EXPIRED},
    ForecastState.SUPERSEDED: {ForecastState.VERIFIED_BY_OUTCOME},
    ForecastState.VERIFIED_BY_OUTCOME: set(),  # Terminal state
    ForecastState.EXPIRED: set(),  # Terminal state
    ForecastState.INVALIDATED: set(),  # Terminal state
    ForecastState.FAILED: set(),  # Terminal state
}


class ForecastHorizon(str, Enum):
    """Configurable temporal horizon bounding prediction horizon (Spec 6)."""

    SHORT = "SHORT"      # e.g. 0 - 24 hours
    MEDIUM = "MEDIUM"    # e.g. 1 - 7 days
    LONG = "LONG"        # e.g. > 7 days


class ForecastType(str, Enum):
    """Forecast categories supported by the engine (Spec 7)."""

    POINT = "POINT"
    INTERVAL = "INTERVAL"
    PROBABILISTIC = "PROBABILISTIC"
    EVENT_PROBABILITY = "EVENT_PROBABILITY"
    TREND = "TREND"
    TRAJECTORY = "TRAJECTORY"
    SCENARIO = "SCENARIO"
    CAUSAL_INTERVENTION = "CAUSAL_INTERVENTION"
    COUNTERFACTUAL = "COUNTERFACTUAL"


class ForecastStrategyType(str, Enum):
    """Forecasting strategy abstraction (Spec 8)."""

    NAIVE_BASELINE = "NAIVE_BASELINE"
    MOVING_AVERAGE = "MOVING_AVERAGE"
    EXPONENTIAL_SMOOTHING = "EXPONENTIAL_SMOOTHING"
    TREND_EXTRAPOLATION = "TREND_EXTRAPOLATION"
    HISTORICAL_SEASONAL = "HISTORICAL_SEASONAL"
    EVENT_CONDITIONED = "EVENT_CONDITIONED"
    CAUSAL = "CAUSAL"
    CAUSAL_INTERVENTION = "CAUSAL_INTERVENTION"
    WORLD_MODEL = "WORLD_MODEL"
    SIMULATION_DERIVED = "SIMULATION_DERIVED"
    MODEL_ROUTER = "MODEL_ROUTER"
    ENSEMBLE = "ENSEMBLE"


class UncertaintyType(str, Enum):
    """Five orthogonal sources of uncertainty (Spec 15)."""

    MODEL_UNCERTAINTY = "MODEL_UNCERTAINTY"
    DATA_UNCERTAINTY = "DATA_UNCERTAINTY"
    PARAMETER_UNCERTAINTY = "PARAMETER_UNCERTAINTY"
    ENVIRONMENTAL_UNCERTAINTY = "ENVIRONMENTAL_UNCERTAINTY"
    SCENARIO_UNCERTAINTY = "SCENARIO_UNCERTAINTY"


class EarlyWarningSeverity(str, Enum):
    """Standardized early warning severity levels (Spec 25) with Task 47 compatibility."""

    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    # Task 47 compatibility
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EarlyWarningState(str, Enum):
    """9-state early warning lifecycle (Spec 65)."""

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    DE_ESCALATED = "DE_ESCALATED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    DISMISSED = "DISMISSED"
    INVALIDATED = "INVALIDATED"


class EarlyWarningResolution(str, Enum):
    """6 explicit early warning resolution modes (Spec 66)."""

    EVENT_OCCURRED = "EVENT_OCCURRED"
    RISK_DECREASED = "RISK_DECREASED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    DATA_INVALIDATED = "DATA_INVALIDATED"
    FORECAST_EXPIRED = "FORECAST_EXPIRED"
    MANUALLY_DISMISSED = "MANUALLY_DISMISSED"


class ForecastHealthStatus(str, Enum):
    """Forecast and model health state (Spec 64)."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNCERTAIN = "UNCERTAIN"
    DRIFTING = "DRIFTING"
    STALE = "STALE"
    UNRELIABLE = "UNRELIABLE"
    FAILED = "FAILED"


# ==================================================
# Structural Domain Artifacts
# ==================================================

class PredictionInterval(BaseModel):
    """Interval forecast range with explicit coverage target (Spec 7, 15)."""

    lower_bound: Optional[float] = None
    lower: Optional[float] = None
    point_estimate: Optional[float] = None
    upper_bound: Optional[float] = None
    upper: Optional[float] = None
    coverage_target: float = Field(0.90, ge=0.50, le=0.99)
    unit: str = ""

    @model_validator(mode="after")
    def populate_bounds(self) -> PredictionInterval:
        if self.lower_bound is None and self.lower is not None:
            self.lower_bound = self.lower
        elif self.lower is None and self.lower_bound is not None:
            self.lower = self.lower_bound

        if self.upper_bound is None and self.upper is not None:
            self.upper_bound = self.upper
        elif self.upper is None and self.upper_bound is not None:
            self.upper = self.upper_bound

        if self.point_estimate is None:
            lb = self.lower_bound if self.lower_bound is not None else 0.0
            ub = self.upper_bound if self.upper_bound is not None else 0.0
            self.point_estimate = round((lb + ub) / 2.0, 4)

        if self.lower_bound is None:
            self.lower_bound = self.point_estimate
            self.lower = self.point_estimate
        if self.upper_bound is None:
            self.upper_bound = self.point_estimate
            self.upper = self.point_estimate
        return self


class BaselineSpec(BaseModel):
    """Deterministic baseline benchmark reference for forecast comparison (Spec 9)."""

    baseline_type: str = "last_observed_value"
    baseline_value: float = 0.0
    baseline_window_seconds: int = 86400
    baseline_data_refs: List[str] = Field(default_factory=list)
    outperformed: Optional[bool] = None
    skill_score: Optional[float] = None


class UncertaintyBreakdown(BaseModel):
    """Granular uncertainty metadata differentiating orthogonal causes (Spec 15)."""

    model_uncertainty: float = Field(0.1, ge=0.0, le=1.0)
    data_uncertainty: float = Field(0.1, ge=0.0, le=1.0)
    parameter_uncertainty: float = Field(0.1, ge=0.0, le=1.0)
    environmental_uncertainty: float = Field(0.1, ge=0.0, le=1.0)
    scenario_spread: float = Field(0.0, ge=0.0, le=1.0)
    qualitative_rationale: str = ""
    composite_uncertainty: float = Field(0.2, ge=0.0, le=1.0)


class LeadingIndicatorSignal(BaseModel):
    """A leading indicator signal that precedes target metric changes (Spec 20)."""

    indicator_id: str
    name: str
    target_metric: str
    direction: str = "increasing"  # increasing, decreasing, erratic
    lead_time_seconds: int = 3600
    historical_reliability: float = Field(0.8, ge=0.0, le=1.0)
    current_value: float = 0.0
    baseline_value: float = 0.0
    deviation: float = 0.0
    is_active: bool = False
    evidence_refs: List[str] = Field(default_factory=list)
    freshness_timestamp: str = Field(default_factory=utc_now_iso)

    @property
    def reliability_score(self) -> float:
        return self.historical_reliability

    @property
    def target(self) -> str:
        return self.target_metric



class ForecastQualityScore(BaseModel):
    """Interpretable composite quality rating (Spec 63)."""

    data_quality: float = Field(0.8, ge=0.0, le=1.0)
    historical_performance: float = Field(0.8, ge=0.0, le=1.0)
    historical_strategy_performance: Optional[float] = None
    calibration_score: float = Field(0.8, ge=0.0, le=1.0)
    recency_score: float = Field(0.8, ge=0.0, le=1.0)
    model_agreement: float = Field(0.8, ge=0.0, le=1.0)
    model_agreement_score: Optional[float] = None
    causal_validity: float = Field(0.8, ge=0.0, le=1.0)
    causal_validity_score: Optional[float] = None
    horizon_difficulty: float = 0.0
    feature_completeness: float = 1.0
    composite_score: Optional[float] = None
    limitations: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def compute_composite(self) -> ForecastQualityScore:
        hp = self.historical_strategy_performance if self.historical_strategy_performance is not None else self.historical_performance
        ma = self.model_agreement_score if self.model_agreement_score is not None else self.model_agreement
        cv = self.causal_validity_score if self.causal_validity_score is not None else self.causal_validity
        if self.composite_score is None:
            raw = (
                self.data_quality * 0.20
                + hp * 0.20
                + self.calibration_score * 0.20
                + self.recency_score * 0.15
                + ma * 0.15
                + cv * 0.10
            ) - (self.horizon_difficulty * 0.05)
            self.composite_score = max(0.0, min(1.0, round(raw, 4)))
        return self

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ForecastVersionRecord(BaseModel):
    """Immutable record of forecast revision (Spec 34, 35)."""

    version: int
    previous_version_id: Optional[str] = None
    change_reason: str
    changed_inputs: Dict[str, Any] = Field(default_factory=dict)
    changed_model: Optional[str] = None
    changed_assumptions: List[str] = Field(default_factory=list)
    likelihood_delta: float = 0.0
    point_estimate_delta: Optional[float] = None
    timestamp: str = Field(default_factory=utc_now_iso)


# ==================================================
# Backward-Compatible Task 47 Schemas
# ==================================================

class ScenarioSchema(BaseModel):
    scenario_id: str
    description: str
    prerequisites: List[str] = Field(default_factory=list)
    expected_state: Dict[str, Any] = Field(default_factory=dict)
    likelihood: float = Field(0.5, ge=0.0, le=1.0)
    impact: float = Field(0.5, ge=0.0, le=1.0)
    evidence: Union[Dict[str, Any], List[Any]] = Field(default_factory=dict)
    is_counterfactual: bool = False


class PredictionCreateRequest(BaseModel):
    subject: str = Field(..., description="Entity or metric targeted (e.g. 'service:api:latency')")
    event: str = Field(..., description="Predicted event or mutation (e.g. 'CAPACITY_EXHAUSTED')")
    predicted_state: Dict[str, Any] = Field(default_factory=dict)
    prediction_window: str = Field("short-term", description="near-term, short-term, medium-term, long-term, or duration")
    time_to_event_seconds: Optional[float] = Field(None, description="Explicit numeric time interval")
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    model_reference: str = Field("trend_linear_v1")
    assumptions: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    environment: str = Field("DEVELOPMENT")


class PredictionResponse(BaseModel):
    prediction_id: str
    subject: str
    event: str
    predicted_state: Dict[str, Any]
    prediction_window: str
    confidence: float
    model_reference: str
    assumptions: List[str]
    evidence_refs: List[str]
    status: str
    scope: Dict[str, Any]
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool = False
    actual_outcome: Optional[Dict[str, Any]] = None
    action_influenced: bool = False


class ForecastCreateRequest(BaseModel):
    target: str = Field(..., description="Target system or domain metric")
    target_type: str = Field("metric", description="metric, event, state, system")
    target_metric: Optional[str] = Field(None, description="Specific metric name (e.g. 'cpu_load')")
    horizon: ForecastHorizon = Field(ForecastHorizon.MEDIUM)
    forecast_type: ForecastType = Field(ForecastType.INTERVAL)
    strategy: ForecastStrategyType = Field(ForecastStrategyType.TREND_EXTRAPOLATION)
    scenarios: List[ScenarioSchema] = Field(default_factory=list)
    likelihood: float = Field(0.5, ge=0.0, le=1.0)
    point_estimate: Optional[float] = None
    predicted_value: Optional[float] = None
    observations: Optional[List[Any]] = None
    historical_series: Optional[List[Any]] = None
    series: Optional[List[Any]] = None
    interval: Optional[PredictionInterval] = None
    timeframe: str = Field("medium-term")
    evidence: Union[Dict[str, Any], List[Any]] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    uncertainty: float = Field(0.2, ge=0.0, le=1.0)
    baseline: Optional[BaselineSpec] = None
    origin_time: Optional[str] = None
    forecast_start: Optional[str] = None
    forecast_end: Optional[str] = None


class ForecastResponse(BaseModel):
    forecast_id: str
    target: str
    target_type: str = "metric"
    target_metric: Optional[str] = None
    horizon: str = "MEDIUM"
    forecast_type: str = "INTERVAL"
    strategy: str = "TREND_EXTRAPOLATION"
    scenarios: List[ScenarioSchema] = Field(default_factory=list)
    likelihood: float
    point_estimate: Optional[float] = None
    predicted_value: Optional[float] = None
    interval: Optional[PredictionInterval] = None
    baseline: Optional[BaselineSpec] = None
    uncertainty_breakdown: Optional[UncertaintyBreakdown] = None
    quality_score: Optional[ForecastQualityScore] = None
    leading_indicators: List[LeadingIndicatorSignal] = Field(default_factory=list)
    timeframe: str
    evidence: Union[Dict[str, Any], List[Any]]
    assumptions: List[str]
    uncertainty: float
    version: int = 1
    previous_version_id: Optional[str] = None
    status: str = "GENERATED"
    state: Optional[str] = None
    health: str = "HEALTHY"
    label: str = "FORECAST"
    created_at: str
    expires_at: Optional[str] = None
    origin_time: Optional[str] = None
    actual_outcome: Optional[Union[float, int, Dict[str, Any], Any]] = None
    scope: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_forecast_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            pv = data.get("predicted_value") if data.get("predicted_value") is not None else data.get("point_estimate")
            if pv is not None:
                if data.get("predicted_value") is None:
                    data["predicted_value"] = pv
                if data.get("point_estimate") is None:
                    data["point_estimate"] = pv

            st = data.get("status") or data.get("state")
            if st is not None:
                st_str = st.value if hasattr(st, "value") else str(st)
                if not data.get("status"):
                    data["status"] = st_str
                if not data.get("state"):
                    data["state"] = st_str

            if "label" not in data or not data["label"]:
                data["label"] = "FORECAST"
        return data



class ForecastRefreshRequest(BaseModel):
    new_evidence: Optional[Dict[str, Any]] = None
    changed_assumptions: Optional[List[str]] = None
    reason: str = "Periodic refresh or telemetry update"


class ForecastInvalidateRequest(BaseModel):
    reason: str = Field(..., description="Reason for invalidating forecast")


class EarlyWarningCreateRequest(BaseModel):
    target: str
    signal: str
    predicted_event: str
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    severity: EarlyWarningSeverity = Field(EarlyWarningSeverity.WARNING)
    expected_window_start: Optional[str] = None
    expected_window_end: Optional[str] = None
    evidence: Union[Dict[str, Any], List[Any]] = Field(default_factory=dict)
    leading_indicators: List[str] = Field(default_factory=list)
    affected_scope: Dict[str, Any] = Field(default_factory=dict)
    linked_forecast_ids: List[str] = Field(default_factory=list)
    recommended_investigation: Optional[str] = None


class EarlyWarningResponse(BaseModel):
    warning_id: str
    target: str
    signal: str
    predicted_event: str
    timeframe: str = "short-term"
    expected_window: Optional[str] = None
    confidence: float
    severity: str
    status: str
    state: Optional[str] = None
    resolution: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_state_and_status(cls, data: Any) -> Any:
        if isinstance(data, dict):
            st = data.get("status") or data.get("state")
            if st is not None:
                st_str = st.value if hasattr(st, "value") else str(st)
                if not data.get("status"):
                    data["status"] = st_str
                if not data.get("state"):
                    data["state"] = st_str
        return data

    evidence: Union[Dict[str, Any], List[Any]]
    leading_indicators: List[str] = Field(default_factory=list)
    linked_forecast_ids: List[str] = Field(default_factory=list)
    recommended_investigation: Optional[str] = None
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool = False
    escalation_count: int = 0
    hysteresis_active: bool = False
    scope: Dict[str, Any] = Field(default_factory=dict)


class EarlyWarningActionRequest(BaseModel):
    reason: str = "User manual interaction"
    resolution: Optional[EarlyWarningResolution] = None


class PredictedRiskResponse(BaseModel):
    risk_id: str
    subject: str
    event: str
    likelihood: float
    impact: float
    risk_score: float
    timeframe: str
    confidence: float
    evidence: Union[Dict[str, Any], List[Any]]
    mitigations: List[str]
    created_at: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    is_high_risk: bool = False


class SimulationRequest(BaseModel):
    target: Optional[str] = None
    scenario_name: Optional[str] = None
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    interventions: List[Dict[str, Any]] = Field(default_factory=list)
    intervention_actions: List[Dict[str, Any]] = Field(default_factory=list)
    steps: Optional[int] = None
    time_steps: int = Field(5, ge=1, le=100)


class SimulationResponse(BaseModel):
    simulation_id: str
    target: str
    label: str = "SIMULATED"  # Strictly marked (Spec 119, 120)
    is_simulated: bool = True
    simulated_steps: List[Dict[str, Any]]
    trajectory: List[Dict[str, Any]] = Field(default_factory=list)
    final_state: Dict[str, Any]
    assumptions: List[str]
    timestamp: str


class CounterfactualRequest(BaseModel):
    subject: str
    current_trend: Optional[Any] = None
    baseline_trend: Optional[Dict[str, Any]] = None
    proposed_action: Optional[str] = None
    hypothetical_intervention: Optional[str] = None
    horizon_hours: int = 24


class CounterfactualResponse(BaseModel):
    counterfactual_id: str
    subject: str
    label: str = "HYPOTHETICAL"  # Strictly marked (Spec 11, 121, 122)
    is_hypothetical: bool = True
    is_historical_fact: bool = False
    hypothesis: str = ""
    no_intervention_outcome: Dict[str, Any] = Field(default_factory=dict)
    intervention_outcome: Optional[Dict[str, Any]] = None
    explanation: str = ""
    timestamp: str


class CalibrationMetricsResponse(BaseModel):
    model_reference: str
    sample_size: int
    brier_score: float
    log_loss: float
    calibration_error: float
    accuracy: float
    expected_calibration_error: float = 0.0
    maximum_calibration_error: float = 0.0
    buckets: List[Dict[str, Any]] = Field(default_factory=list)
    is_degraded: bool = False
    last_evaluated_at: Optional[str] = None


CalibrationReport = CalibrationMetricsResponse


class PredictionHealthResponse(BaseModel):
    predictions_active: int
    predictions_total: int
    forecasts_active: int = 0
    forecasts_total: int = 0
    warnings_open: int
    monitors_running: int
    avg_confidence: float
    brier_score: float
    calibration_quality: str
    drift_status: str = "HEALTHY"
    strategies_summary: Dict[str, Any] = Field(default_factory=dict)


# ==================================================
# Backtesting & Evaluation Schemas
# ==================================================

class BacktestConfig(BaseModel):
    target: str
    strategy: ForecastStrategyType = ForecastStrategyType.TREND_EXTRAPOLATION
    horizon_steps: int = 5
    window_type: str = "rolling"  # rolling, expanding, fixed
    min_train_size: int = 10
    step_size: int = 1
    leakage_check_strict: bool = True


class BacktestResult(BaseModel):
    target: str
    strategy: str
    folds_evaluated: int
    mae: float
    rmse: float
    smape: float
    coverage_rate: float
    baseline_mae: float
    baseline_rmse: float
    skill_score_msss: float
    temporal_isolation_verified: bool
    evaluation_records: List[Dict[str, Any]] = Field(default_factory=list)


class DriftReport(BaseModel):
    target: str
    drift_detected: bool
    drift_type: str = "NONE"  # INPUT, FEATURE, RESIDUAL, CALIBRATION, REGIME_CHANGE
    p_value_or_score: float = 0.0
    threshold: float = 0.05
    description: str = "No statistically meaningful drift detected"
    recommended_action: str = "Maintain current forecast cadence"
    timestamp: str = Field(default_factory=utc_now_iso)

