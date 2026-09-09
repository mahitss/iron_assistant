"""Pydantic Request and Response Schemas for Prediction REST API (Task 47)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


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
    target: str = Field(..., description="Target system or domain")
    scenarios: List[ScenarioSchema] = Field(default_factory=list)
    likelihood: float = Field(0.5, ge=0.0, le=1.0)
    timeframe: str = Field("medium-term")
    evidence: Union[Dict[str, Any], List[Any]] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    uncertainty: float = Field(0.2, ge=0.0, le=1.0)


class ForecastResponse(BaseModel):
    forecast_id: str
    target: str
    scenarios: List[ScenarioSchema]
    likelihood: float
    timeframe: str
    evidence: Union[Dict[str, Any], List[Any]]
    assumptions: List[str]
    uncertainty: float
    version: int
    created_at: str


class EarlyWarningResponse(BaseModel):
    warning_id: str
    target: str
    signal: str
    predicted_event: str
    timeframe: str
    confidence: float
    severity: str
    status: str
    evidence: Union[Dict[str, Any], List[Any]]
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool = False
    escalation_count: int = 0
    scope: Dict[str, Any] = Field(default_factory=dict)


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
    last_evaluated_at: Optional[str] = None


class PredictionHealthResponse(BaseModel):
    predictions_active: int
    predictions_total: int
    warnings_open: int
    monitors_running: int
    avg_confidence: float
    brier_score: float
    calibration_quality: str
