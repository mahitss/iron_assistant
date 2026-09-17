"""SQLAlchemy ORM models for Kairo Real-Time Situational Awareness, Signal Fusion & Proactive Response Orchestrator (Task 60 & Task 99)."""

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
    """Synthesized real-time operational situation representing correlated signals and system impact."""

    __tablename__ = "situations"

    # Core identification & scope
    situation_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Classification & Lifecycle
    situation_type: Mapped[str] = mapped_column(String(32), default="INCIDENT", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DETECTED", index=True, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="DETECTED", index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Timestamps & Time Windows
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )
    first_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Evaluation Dimensions
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", index=True, nullable=False)
    priority: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    novelty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    urgency: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    observability_quality: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    freshness: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    environment: Mapped[str] = mapped_column(String(64), default="development", index=True, nullable=False)

    # Affected Scopes
    affected_entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_resources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_goals: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_workflows: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_agents: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_projects: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_plans: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Correlation & Lineage
    source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    correlation_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    duplicate_group: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_situation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supersedes_situation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merged_from_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    merged_into_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    split_from_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Reasoning & Status
    causal_status: Mapped[str] = mapped_column(String(32), default="CORRELATED", nullable=False)
    state_reconciliation_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", nullable=False)
    recommended_next_step: Mapped[str | None] = mapped_column(String(256), nullable=True)
    current_decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_action_transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Structural & Audit Details
    current_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    expected_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    risk_assessment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    next_steps: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    flapping_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    events: Mapped[list[NormalizedEventModel]] = relationship(
        "NormalizedEventModel", back_populates="situation", cascade="all, delete-orphan"
    )
    signals: Mapped[list[SignalModel]] = relationship(
        "SignalModel", back_populates="situation", cascade="all, delete-orphan"
    )
    hypotheses: Mapped[list[CausalHypothesisModel]] = relationship(
        "CausalHypothesisModel", back_populates="situation", cascade="all, delete-orphan"
    )
    interventions: Mapped[list[SituationInterventionModel]] = relationship(
        "SituationInterventionModel", back_populates="situation", cascade="all, delete-orphan"
    )
    suppressions: Mapped[list[SituationSuppressionModel]] = relationship(
        "SituationSuppressionModel", back_populates="situation", cascade="all, delete-orphan"
    )


class SignalModel(Base):
    """Normalized ingested signal record with multi-source provenance."""

    __tablename__ = "situation_signals"

    signal_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    situation_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("situations.situation_id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signal_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", nullable=False)
    payload_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    freshness: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    trust_classification: Mapped[str] = mapped_column(String(64), default="TRUSTED_INTERNAL", nullable=False)
    sensitivity_classification: Mapped[str] = mapped_column(String(64), default="INTERNAL", nullable=False)

    correlation_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    causal_references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    world_state_references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    decision_action_references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    trace_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    situation: Mapped[SituationModel | None] = relationship("SituationModel", back_populates="signals")


class SituationInterventionModel(Base):
    """Proactive intervention proposals and executed actions linked to situations."""

    __tablename__ = "situation_interventions"

    intervention_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    situation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("situations.situation_id", ondelete="CASCADE"), index=True, nullable=False
    )
    decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_name: Mapped[str] = mapped_column(String(128), nullable=False)
    action_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    emergency_stopped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)

    situation: Mapped[SituationModel] = relationship("SituationModel", back_populates="interventions")


class SituationSuppressionModel(Base):
    """Auditable suppression record silencing non-actionable situations."""

    __tablename__ = "situation_suppressions"

    suppression_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    situation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("situations.situation_id", ondelete="CASCADE"), index=True, nullable=False
    )
    suppressed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    situation: Mapped[SituationModel] = relationship("SituationModel", back_populates="suppressions")


class SituationPatternModel(Base):
    """Recognized historical recurring pattern of operational situations."""

    __tablename__ = "situation_patterns"

    pattern_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    pattern_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    mean_interval_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    historical_situation_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    trend: Mapped[str] = mapped_column(String(32), default="STABLE", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class SituationContextModel(Base):
    """Bounded contextual snapshot compiled for downstream reasoning engines."""

    __tablename__ = "situation_contexts"

    context_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    situation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    observations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    related_entities: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    risk_findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    forecasts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    goals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    recent_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    world_state_diffs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence_provenance: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    is_sanitized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


# Legacy Task 60 models preserved for full backward compatibility
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
