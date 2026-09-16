"""SQLAlchemy models for Task 95 Action Transactions and Execution Governance."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(UTC)


class ActionTransactionModel(Base):
    """Durable relational representation of an Action Transaction."""
    __tablename__ = "action_transactions"

    transaction_id = Column(String(64), primary_key=True, index=True)
    decision_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    workflow_id = Column(String(64), nullable=True, index=True)
    capability_id = Column(String(128), nullable=False, index=True)
    capability_version = Column(String(32), nullable=False, default="1.0.0")
    action_reference = Column(String(256), nullable=False)

    status = Column(String(32), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)

    target_json = Column(JSON, nullable=False, default=dict)
    parameters_json = Column(JSON, nullable=False, default=dict)

    # Authority references
    authorization_reference = Column(String(128), nullable=True)
    approval_reference = Column(String(128), nullable=True)
    governance_reference = Column(String(128), nullable=True)
    resource_reference = Column(String(128), nullable=True)

    # Preflight, Observations, Postconditions
    preflight_checks_json = Column(JSON, nullable=False, default=list)
    observations_json = Column(JSON, nullable=False, default=list)
    postconditions_json = Column(JSON, nullable=False, default=list)
    verification_state = Column(String(32), nullable=False, default="NOT_STARTED")

    # Outcome
    outcome_type = Column(String(32), nullable=True)
    outcome_summary_json = Column(JSON, nullable=False, default=dict)
    deviation_score = Column(Float, nullable=False, default=0.0)
    regret_score = Column(Float, nullable=False, default=0.0)

    # Timestamps & Metadata
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)
    user_id = Column(String(64), nullable=False, default="default_user")
    correlation_id = Column(String(64), nullable=True, index=True)
    trace_id = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_action_txn_status_created", "status", "created_at"),
        Index("ix_action_txn_decision_status", "decision_id", "status"),
    )
