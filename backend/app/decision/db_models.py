"""SQLAlchemy ORM models for Task 94 Decision Intelligence and Decision Memory.

Provides durable, versioned, auditable persistence for decisions, options, assumptions, and outcomes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_hex(prefix: str, length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


class DecisionV2Model(Base):
    """Authoritative decision entity recording deliberation state and resolution."""

    __tablename__ = "decisions_v2"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("drec"))
    decision_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    objective_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="PROPOSED", nullable=False, index=True)
    decision_type: Mapped[str] = mapped_column(String(32), server_default="ACTION", nullable=False, index=True)
    selected_option_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    certainty: Mapped[str] = mapped_column(String(32), server_default="MEDIUM", nullable=False)
    risk_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    resource_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    governance_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    security_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    approval_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expected_outcomes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    actual_outcomes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), server_default="UNVERIFIED", nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_dec2_obj_status", "objective_id", "status"),
        Index("ix_dec2_type_status", "decision_type", "status"),
        Index("ix_dec2_created", "created_at"),
    )


class DecisionOptionV2Model(Base):
    """Candidate or evaluated option within a decision."""

    __tablename__ = "decision_options_v2"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("dopt"))
    option_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, server_default="")
    option_type: Mapped[str] = mapped_column(String(32), server_default="ACTION", nullable=False)
    action_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_feasible: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    is_dominated: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversibility: Mapped[str] = mapped_column(String(32), server_default="REVERSIBLE", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.8", nullable=False)
    scores_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tradeoffs_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_dopt2_dec_feasible", "decision_id", "is_feasible"),
        Index("ix_dopt2_dec_type", "decision_id", "option_type"),
    )


class DecisionAssumptionModel(Base):
    """Auditable assumption record tied to a decision."""

    __tablename__ = "decision_assumptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("dasm"))
    assumption_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(128), server_default="deliberation", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.8", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="ACTIVE", nullable=False, index=True)
    impact_if_false: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_dasm_dec_status", "decision_id", "status"),
    )


class DecisionOutcomeV2Model(Base):
    """Post-execution verification and deviation tracking record."""

    __tablename__ = "decision_outcomes_v2"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("dout"))
    outcome_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    predicted_outcome: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    actual_outcome: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    deviation_score: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    execution_cost: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), server_default="VERIFIED", nullable=False)
    lessons_learned: Mapped[list[str]] = mapped_column(JSON, default=list)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_dout2_dec_verif", "decision_id", "verification_status"),
    )
