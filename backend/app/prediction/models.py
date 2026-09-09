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
