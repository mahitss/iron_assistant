"""SQLAlchemy ORM models for Kairo Executive Decision Engine (Task 57)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String, Text

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DecisionRequestModel(Base):
    __tablename__ = "decision_requests"

    id = Column(String(64), primary_key=True, default=lambda: f"dreq_{uuid.uuid4().hex[:12]}")
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    question = Column(Text, nullable=False)
    intent = Column(String(128), nullable=True)
    context_scope = Column(String(64), nullable=False, default="PROJECT")
    scope_id = Column(String(128), nullable=True)
    authority = Column(String(128), nullable=False, default="user")
    deadline = Column(DateTime(timezone=True), nullable=True)
    risk_tolerance = Column(String(32), nullable=False, default="MEDIUM")
    status = Column(String(64), nullable=False, default="ANALYZING")
    context_snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_dreq_scope_status", "context_scope", "status"),
    )


class DecisionRecordModel(Base):
    __tablename__ = "decision_records"

    id = Column(String(64), primary_key=True, default=lambda: f"drec_{uuid.uuid4().hex[:12]}")
    decision_id = Column(String(64), unique=True, nullable=False, index=True)
    request_id = Column(String(64), nullable=False, index=True)
    status = Column(String(64), nullable=False, default="RECOMMENDED")
    recommendation = Column(JSON, nullable=False, default=dict)
    selected_option_id = Column(String(64), nullable=True)
    selected_by = Column(String(128), nullable=True)
    user_override = Column(Boolean, nullable=False, default=False)
    confidence = Column(Float, nullable=False, default=0.8)
    ranking = Column(JSON, nullable=False, default=list)
    decision_gates = Column(JSON, nullable=False, default=dict)
    approval_required = Column(Boolean, nullable=False, default=False)
    approval_id = Column(String(64), nullable=True)
    execution_plan = Column(JSON, nullable=True)
    verification_plan = Column(JSON, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    provenance = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_drec_status_created", "status", "created_at"),
    )


class DecisionOptionModel(Base):
    __tablename__ = "decision_options"

    id = Column(String(64), primary_key=True, default=lambda: f"dopt_{uuid.uuid4().hex[:12]}")
    option_id = Column(String(64), unique=True, nullable=False, index=True)
    decision_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False, default="")
    option_type = Column(String(64), nullable=False, default="STANDARD")
    score = Column(Float, nullable=False, default=0.0)
    rank = Column(Integer, nullable=False, default=0)
    is_feasible = Column(Boolean, nullable=False, default=True)
    rejection_reason = Column(String(256), nullable=True)
    reversibility = Column(String(64), nullable=False, default="REVERSIBLE")
    metrics = Column(JSON, nullable=False, default=dict)
    tradeoffs = Column(JSON, nullable=False, default=list)
    risks = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_dopt_dec_score", "decision_id", "score"),
    )


class DecisionCommitmentModel(Base):
    __tablename__ = "decision_commitments"

    id = Column(String(64), primary_key=True, default=lambda: f"dcom_{uuid.uuid4().hex[:12]}")
    commitment_id = Column(String(64), unique=True, nullable=False, index=True)
    decision_id = Column(String(64), nullable=False, index=True)
    owner = Column(String(128), nullable=False)
    title = Column(String(256), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(64), nullable=False, default="PROPOSED")
    authorized_by = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_dcom_status", "status"),
    )


class DecisionOutcomeModel(Base):
    __tablename__ = "decision_outcomes"

    id = Column(String(64), primary_key=True, default=lambda: f"dout_{uuid.uuid4().hex[:12]}")
    outcome_id = Column(String(64), unique=True, nullable=False, index=True)
    decision_id = Column(String(64), nullable=False, index=True)
    actual_benefit = Column(Float, nullable=False, default=0.0)
    actual_cost = Column(Float, nullable=False, default=0.0)
    actual_duration = Column(Float, nullable=False, default=0.0)
    prediction_error = Column(Float, nullable=False, default=0.0)
    unexpected_side_effects = Column(JSON, nullable=False, default=list)
    success = Column(Boolean, nullable=False, default=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    metadata_json = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_dout_dec_id", "decision_id"),
    )


class DecisionRevisionModel(Base):
    __tablename__ = "decision_revisions"

    id = Column(String(64), primary_key=True, default=lambda: f"drev_{uuid.uuid4().hex[:12]}")
    revision_id = Column(String(64), unique=True, nullable=False, index=True)
    parent_decision_id = Column(String(64), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False, default=1)
    reason = Column(Text, nullable=False)
    actor = Column(String(128), nullable=False)
    previous_snapshot = Column(JSON, nullable=False, default=dict)
    new_snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_drev_parent_num", "parent_decision_id", "revision_number"),
    )
