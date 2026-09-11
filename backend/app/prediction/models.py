"""SQLAlchemy Database Models for Kairo Predictive Intelligence & Anticipation Engine (Task 47)."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PredictionModel(Base):
    """Persistent storage for bounded environmental state predictions (Spec 2-5)."""

    __tablename__ = "predictions"

    id = Column(String(64), primary_key=True, default=lambda: f"pred_{uuid.uuid4().hex[:12]}")
    subject = Column(String(256), nullable=False, index=True)
    event = Column(String(128), nullable=False)
    predicted_state = Column(JSON, nullable=False, default=dict)
    prediction_window = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    model_reference = Column(String(128), nullable=False)
    assumptions = Column(JSON, nullable=False, default=list)
    evidence_refs = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="ACTIVE", index=True)
    scope_data = Column(JSON, nullable=False, default=dict)
    actual_outcome = Column(JSON, nullable=True)
    action_influenced = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)


class ForecastModel(Base):
    """Persistent multi-scenario future projections (Spec 6-11)."""

    __tablename__ = "forecasts"

    id = Column(String(64), primary_key=True, default=lambda: f"fc_{uuid.uuid4().hex[:12]}")
    target = Column(String(256), nullable=False, index=True)
    scenarios = Column(JSON, nullable=False, default=list)
    likelihood = Column(Float, nullable=False, default=0.5)
    timeframe = Column(String(64), nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    assumptions = Column(JSON, nullable=False, default=list)
    uncertainty = Column(Float, nullable=False, default=0.2)
    version = Column(Integer, nullable=False, default=1)
    previous_version_id = Column(String(64), nullable=True)
    scope_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class EarlyWarningModel(Base):
    """Persistent ledger of proactive early warnings and incident flags (Spec 30-40)."""

    __tablename__ = "early_warnings"

    id = Column(String(64), primary_key=True, default=lambda: f"ew_{uuid.uuid4().hex[:12]}")
    target = Column(String(256), nullable=False, index=True)
    signal = Column(String(128), nullable=False)
    predicted_event = Column(String(256), nullable=False)
    timeframe = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    severity = Column(String(32), nullable=False, default="INFO", index=True)
    status = Column(String(32), nullable=False, default="OPEN", index=True)
    evidence = Column(JSON, nullable=False, default=dict)
    scope_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class PredictedRiskModel(Base):
    """Persistent store for anticipated failure/incident risks and mitigations (Spec 41-46)."""

    __tablename__ = "predicted_risks"

    id = Column(String(64), primary_key=True, default=lambda: f"risk_{uuid.uuid4().hex[:12]}")
    subject = Column(String(256), nullable=False, index=True)
    event = Column(String(256), nullable=False)
    likelihood = Column(Float, nullable=False, default=0.5)
    impact = Column(Float, nullable=False, default=0.5)
    risk_score = Column(Float, nullable=False, index=True)
    timeframe = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    evidence = Column(JSON, nullable=False, default=dict)
    mitigations = Column(JSON, nullable=False, default=list)
    scope_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class PredictionTriggerModel(Base):
    """Persistent preemptive action trigger rules with policy gating (Spec 50-56)."""

    __tablename__ = "prediction_triggers"

    id = Column(String(64), primary_key=True, default=lambda: f"trig_{uuid.uuid4().hex[:12]}")
    condition_expr = Column(String(256), nullable=False)
    trigger_type = Column(String(32), nullable=False)
    action_class = Column(String(32), nullable=False)
    required_evidence = Column(JSON, nullable=False, default=list)
    authorization_scope = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="ACTIVE", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class PredictionCalibrationModel(Base):
    """Empirical calibration metrics tracking forecast accuracy over time (Spec 19-23, 110)."""

    __tablename__ = "prediction_calibrations"

    id = Column(String(64), primary_key=True, default=lambda: f"calib_{uuid.uuid4().hex[:12]}")
    model_reference = Column(String(128), nullable=False, index=True)
    sample_size = Column(Integer, nullable=False, default=0)
    brier_score = Column(Float, nullable=False, default=0.0)
    log_loss = Column(Float, nullable=False, default=0.0)
    calibration_error = Column(Float, nullable=False, default=0.0)
    accuracy = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)


# ==================================================
# Task 74 Persistent Entities
# ==================================================

class ForecastVersionModel(Base):
    """Persistent version history of forecasts across revisions (Spec 34, 35)."""

    __tablename__ = "forecast_versions"

    id = Column(String(64), primary_key=True, default=lambda: f"fcv_{uuid.uuid4().hex[:12]}")
    forecast_id = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    previous_version_id = Column(String(64), nullable=True)
    change_reason = Column(Text, nullable=False, default="")
    changed_inputs = Column(JSON, nullable=False, default=dict)
    changed_model = Column(String(128), nullable=True)
    changed_assumptions = Column(JSON, nullable=False, default=list)
    likelihood_delta = Column(Float, nullable=False, default=0.0)
    point_estimate_delta = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ForecastEvaluationModel(Base):
    """Persistent evaluation results comparing forecasts against ground truth reality (Spec 13, 33)."""

    __tablename__ = "forecast_evaluations"

    id = Column(String(64), primary_key=True, default=lambda: f"fce_{uuid.uuid4().hex[:12]}")
    forecast_id = Column(String(64), nullable=False, index=True)
    target = Column(String(256), nullable=False, index=True)
    realized_outcome = Column(JSON, nullable=False, default=dict)
    realized_value = Column(Float, nullable=True)
    error_metrics = Column(JSON, nullable=False, default=dict)  # MAE, RMSE, sMAPE, Brier
    baseline_comparison = Column(JSON, nullable=False, default=dict)  # skill_score, outperformance
    action_influenced = Column(Boolean, nullable=False, default=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ForecastLeadingIndicatorModel(Base):
    """Persistent tracking of leading indicators and historical correlation (Spec 20)."""

    __tablename__ = "forecast_leading_indicators"

    id = Column(String(64), primary_key=True, default=lambda: f"fli_{uuid.uuid4().hex[:12]}")
    indicator_id = Column(String(128), nullable=False, unique=True, index=True)
    target_metric = Column(String(128), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    direction = Column(String(32), nullable=False, default="increasing")
    lead_time_seconds = Column(Integer, nullable=False, default=3600)
    historical_reliability = Column(Float, nullable=False, default=0.8)
    current_value = Column(Float, nullable=False, default=0.0)
    baseline_value = Column(Float, nullable=False, default=0.0)
    deviation = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=False)
    evidence_refs = Column(JSON, nullable=False, default=list)
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ForecastDriftModel(Base):
    """Persistent audit of statistical and behavioural drift events (Spec 23)."""

    __tablename__ = "forecast_drifts"

    id = Column(String(64), primary_key=True, default=lambda: f"drf_{uuid.uuid4().hex[:12]}")
    target = Column(String(256), nullable=False, index=True)
    drift_type = Column(String(64), nullable=False, index=True)  # INPUT, FEATURE, RESIDUAL, CALIBRATION
    p_value_or_score = Column(Float, nullable=False, default=0.0)
    threshold = Column(Float, nullable=False, default=0.05)
    description = Column(Text, nullable=False, default="")
    action_taken = Column(String(128), nullable=False, default="LOGGED")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ForecastWarningRecordModel(Base):
    """Persistent record of early warnings with hysteresis and deduplication tracking (Spec 24-27, 65, 66)."""

    __tablename__ = "forecast_warning_records"

    id = Column(String(64), primary_key=True, default=lambda: f"fwr_{uuid.uuid4().hex[:12]}")
    warning_id = Column(String(64), nullable=False, unique=True, index=True)
    fingerprint = Column(String(128), nullable=False, index=True)
    target = Column(String(256), nullable=False, index=True)
    signal = Column(String(128), nullable=False)
    predicted_event = Column(String(256), nullable=False)
    severity = Column(String(32), nullable=False, default="INFO", index=True)
    status = Column(String(32), nullable=False, default="CREATED", index=True)
    confidence = Column(Float, nullable=False, default=0.5)
    hysteresis_state = Column(JSON, nullable=False, default=dict)
    resolution = Column(String(64), nullable=True)
    lead_time_seconds = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=False, default=dict)
    scope_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

