"""SQLAlchemy ORM models for Kairo Real-Time Situational Awareness & Event Correlation Engine (Task 60)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SituationModel(Base):
    """Synthesized real-time operational situation representing correlated events and system impact."""

    __tablename__ = "situations"

    situation_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DETECTED", index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="development", index=True, nullable=False)
    affected_resources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_plans: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_goals: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    current_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    expected_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    risk_assessment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    next_steps: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    flapping_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    events: Mapped[list[NormalizedEventModel]] = relationship(
        "NormalizedEventModel", back_populates="situation", cascade="all, delete-orphan"
    )
    hypotheses: Mapped[list[CausalHypothesisModel]] = relationship(
        "CausalHypothesisModel", back_populates="situation", cascade="all, delete-orphan"
    )


class NormalizedEventModel(Base):
    """Normalized ingested telemetry and observation events with provenance."""

    __tablename__ = "situation_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    situation_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("situations.situation_id", ondelete="SET NULL"), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_trust: Mapped[str] = mapped_column(String(64), default="TRUSTED_SYSTEM", nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="development", nullable=False)
    resource: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="INFO", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    situation: Mapped[SituationModel | None] = relationship("SituationModel", back_populates="events")


class SignalBaselineModel(Base):
    """Statistical metric baselines protected against incident poisoning."""

    __tablename__ = "signal_baselines"

    baseline_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    signal_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="development", nullable=False)
    mean_val: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    min_val: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_val: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_calibrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )


class CausalHypothesisModel(Base):
    """Plausible causal explanations for observed situations."""

    __tablename__ = "situation_hypotheses"

    hypothesis_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    situation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("situations.situation_id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_cause: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(32), default="LIKELY", nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommended_diagnostics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    situation: Mapped[SituationModel] = relationship("SituationModel", back_populates="hypotheses")


class SituationAuditModel(Base):
    """Tamper-evident append-only audit trail for situational awareness events."""

    __tablename__ = "situation_audit_log"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    situation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
