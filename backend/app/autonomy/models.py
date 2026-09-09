"""SQLAlchemy database models for Kairo Autonomous Execution & Long-Horizon Agency Engine (Task 45)."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AutonomousGoalModel(Base):
    """Persistent storage for high-level user objectives (Spec 2, 7)."""

    __tablename__ = "autonomous_goals"

    id = Column(String(64), primary_key=True, default=lambda: f"goal_{uuid.uuid4().hex[:12]}")
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, default="default_project", index=True)
    status = Column(String(32), nullable=False, default="ACTIVE")
    success_criteria = Column(JSON, nullable=False, default=list)
    hard_constraints = Column(JSON, nullable=False, default=list)
    scope_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class AutonomousRunModel(Base):
    """Execution state machine instance tracking an autonomous run across long cycles (Spec 2, 3)."""

    __tablename__ = "autonomous_runs"

    id = Column(String(64), primary_key=True, default=lambda: f"run_{uuid.uuid4().hex[:12]}")
    goal_id = Column(String(64), ForeignKey("autonomous_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String(64), nullable=False, default="default_plan")
    plan_version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="CREATED", index=True)
    autonomy_level = Column(String(32), nullable=False, default="AUTONOMOUS")
    owner_user_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, default="default_project", index=True)
    current_step_id = Column(String(64), nullable=True)
    progress_pct = Column(Float, nullable=False, default=0.0)
    budget_data = Column(JSON, nullable=False, default=dict)
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    last_checkpoint_id = Column(String(64), nullable=True)
    active_lease_id = Column(String(64), nullable=True)
    lease_owner = Column(String(64), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_autonomous_runs_owner_status", "owner_user_id", "status"),
        Index("ix_autonomous_runs_lease", "active_lease_id", "lease_expires_at"),
    )


class AutonomousCheckpointModel(Base):
    """Durable state snapshot for crash recovery, pause/resume, and rollbacks (Spec 10, 11)."""

    __tablename__ = "autonomous_checkpoints"

    id = Column(String(64), primary_key=True, default=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    run_id = Column(String(64), ForeignKey("autonomous_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_version = Column(Integer, nullable=False, default=1)
    step_id = Column(String(64), nullable=True)
    run_state = Column(String(32), nullable=False)
    completed_work = Column(JSON, nullable=False, default=list)
    pending_work = Column(JSON, nullable=False, default=list)
    active_work = Column(JSON, nullable=False, default=list)
    evidence_refs = Column(JSON, nullable=False, default=list)
    verification_state = Column(JSON, nullable=False, default=dict)
    budget_state = Column(JSON, nullable=False, default=dict)
    world_state_version = Column(String(64), nullable=True)
    agent_state = Column(JSON, nullable=False, default=dict)
    is_valid = Column(Boolean, nullable=False, default=True)
    corruption_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class AutonomousCompletionRecordModel(Base):
    """Immutable certificate of verified goal completion (Spec 155, 156)."""

    __tablename__ = "autonomous_completion_records"

    id = Column(String(64), primary_key=True, default=lambda: f"comp_{uuid.uuid4().hex[:12]}")
    run_id = Column(String(64), ForeignKey("autonomous_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    goal_id = Column(String(64), nullable=False, index=True)
    plan_version = Column(Integer, nullable=False)
    success_criteria = Column(JSON, nullable=False, default=list)
    verification_results = Column(JSON, nullable=False, default=list)
    evidence_refs = Column(JSON, nullable=False, default=list)
    remaining_uncertainty = Column(JSON, nullable=False, default=list)
    completed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class AutonomousJournalEntryModel(Base):
    """Append-only, immutable execution audit journal (Spec 129, 130)."""

    __tablename__ = "autonomous_journal_entries"

    id = Column(String(64), primary_key=True, default=lambda: f"jrn_{uuid.uuid4().hex[:12]}")
    run_id = Column(String(64), ForeignKey("autonomous_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    step_id = Column(String(64), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    sequence_num = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_autonomous_journal_run_seq", "run_id", "sequence_num", unique=True),
    )
