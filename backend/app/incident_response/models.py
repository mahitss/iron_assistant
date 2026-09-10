"""SQLAlchemy ORM models for Kairo Incident Response & Recovery Autonomy Engine (Task 61)."""

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


class IncidentResponseModel(Base):
    """Core incident response entity tracking incident lifecycle, triage, responders, and resolution."""

    __tablename__ = "incident_responses"

    response_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    situation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DETECTED", index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", index=True, nullable=False)
    urgency: Mapped[str] = mapped_column(String(32), default="NORMAL", index=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="development", index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Scopes
    affected_resources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_plans: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    affected_goals: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Responder command
    responders: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    incident_commander: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Decisions and Actions
    selected_option_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    automation_level: Mapped[str] = mapped_column(String(32), default="RECOMMEND", nullable=False)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    hypotheses: Mapped[list[IncidentHypothesisModel]] = relationship(
        "IncidentHypothesisModel", back_populates="incident", cascade="all, delete-orphan"
    )
    actions: Mapped[list[IncidentActionModel]] = relationship(
        "IncidentActionModel", back_populates="incident", cascade="all, delete-orphan"
    )
    postmortem: Mapped[IncidentPostmortemModel | None] = relationship(
        "IncidentPostmortemModel", back_populates="incident", uselist=False, cascade="all, delete-orphan"
    )


class IncidentHypothesisModel(Base):
    """Candidate causal explanations with supporting/contradictory evidence."""

    __tablename__ = "incident_hypotheses"

    hypothesis_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("incident_responses.incident_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    candidate_cause: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED", index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    evidence_supporting: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence_contradictory: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    recommended_diagnostics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    incident: Mapped[IncidentResponseModel] = relationship(
        "IncidentResponseModel", back_populates="hypotheses"
    )


class IncidentActionModel(Base):
    """Discrete operational actions (diagnostics, containment, rollback, failover, recovery) planned or executed."""

    __tablename__ = "incident_actions"

    action_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("incident_responses.incident_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED", index=True, nullable=False)
    is_reversible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_idempotent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    executor_role: Mapped[str] = mapped_column(String(64), default="OPERATOR", nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    verification_spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    execution_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped[IncidentResponseModel] = relationship("IncidentResponseModel", back_populates="actions")


class IncidentRecoveryPlanModel(Base):
    """Multi-step recovery plan with checkpoints, barriers, and rollback paths."""

    __tablename__ = "incident_recovery_plans"

    plan_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="NOT_STARTED", index=True, nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checkpoints: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    rollback_strategy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )


class IncidentPostmortemModel(Base):
    """Structured blameless post-incident review capturing root causes, contributing factors, and preventive items."""

    __tablename__ = "incident_postmortems"

    postmortem_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("incident_responses.incident_id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(String(256), default="ROOT_CAUSE_UNKNOWN", nullable=False)
    contributing_factors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    what_worked: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    what_failed: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    action_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    lessons_learned: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    incident: Mapped[IncidentResponseModel] = relationship(
        "IncidentResponseModel", back_populates="postmortem"
    )


class IncidentAuditModel(Base):
    """Immutable append-only audit trail with SHA-256 cryptographic hash chaining."""

    __tablename__ = "incident_audits"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    incident_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
