"""SQLAlchemy ORM models for Executive Memory & Long-Horizon Context Engine (Task 53)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Index, JSON, String, Text
from app.db.session import Base


class ExecutiveStateModel(Base):
    __tablename__ = "executive_states"

    id = Column(String(64), primary_key=True, default=lambda: f"exs_{uuid.uuid4().hex[:12]}")
    state_id = Column(String(64), unique=True, nullable=False, index=True)
    scope = Column(String(64), nullable=False, default="PROJECT")
    scope_id = Column(String(128), nullable=True)
    active_projects = Column(JSON, nullable=False, default=list)
    active_goals = Column(JSON, nullable=False, default=list)
    active_tasks = Column(JSON, nullable=False, default=list)
    blockers = Column(JSON, nullable=False, default=list)
    open_loops = Column(JSON, nullable=False, default=list)
    recent_decisions = Column(JSON, nullable=False, default=list)
    recent_outcomes = Column(JSON, nullable=False, default=list)
    upcoming_deadlines = Column(JSON, nullable=False, default=list)
    pending_commitments = Column(JSON, nullable=False, default=list)
    next_actions = Column(JSON, nullable=False, default=list)
    risks = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=1.0)
    provenance = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_executive_states_scope_idx", "scope", "scope_id"),
        Index("ix_executive_states_ts_idx", "timestamp"),
    )


class TimelineEventModel(Base):
    __tablename__ = "timeline_events"

    id = Column(String(64), primary_key=True, default=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    source = Column(String(64), nullable=False)
    project_id = Column(String(128), nullable=True, index=True)
    actor = Column(String(128), nullable=False)
    description_reference = Column(Text, nullable=False)
    impact = Column(String(64), nullable=False, default="MEDIUM")
    provenance = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_timeline_events_type_ts_idx", "event_type", "timestamp"),
    )


class OpenLoopModel(Base):
    __tablename__ = "open_loops"

    id = Column(String(64), primary_key=True, default=lambda: f"loop_{uuid.uuid4().hex[:12]}")
    loop_id = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    owner = Column(String(128), nullable=False)
    source = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="OPEN", index=True)
    priority = Column(Float, nullable=False, default=1.0)
    scope = Column(String(64), nullable=False, default="PROJECT")
    scope_id = Column(String(128), nullable=True)
    dependencies = Column(JSON, nullable=False, default=list)
    due_at = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_open_loops_status_priority_idx", "status", "priority"),
        Index("ix_open_loops_scope_idx", "scope", "scope_id"),
    )


class BlockerModel(Base):
    __tablename__ = "blockers"

    id = Column(String(64), primary_key=True, default=lambda: f"blk_{uuid.uuid4().hex[:12]}")
    blocker_id = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    affected_tasks = Column(JSON, nullable=False, default=list)
    source = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False, default="HIGH")
    owner = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE", index=True)
    causality_evidence = Column(JSON, nullable=False, default=dict)
    detected_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_blockers_status_severity_idx", "status", "severity"),
    )


class MilestoneModel(Base):
    __tablename__ = "milestones"

    id = Column(String(64), primary_key=True, default=lambda: f"mls_{uuid.uuid4().hex[:12]}")
    milestone_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(String(128), nullable=False, index=True)
    goal_id = Column(String(128), nullable=True)
    title = Column(String(256), nullable=False)
    criteria = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="PLANNED", index=True)
    evidence = Column(JSON, nullable=False, default=dict)
    due_at = Column(DateTime(timezone=True), nullable=True)
    achieved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ExecutiveSummaryModel(Base):
    __tablename__ = "executive_summaries"

    id = Column(String(64), primary_key=True, default=lambda: f"brf_{uuid.uuid4().hex[:12]}")
    summary_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(String(128), nullable=False, index=True)
    current_brief = Column(Text, nullable=False)
    recent_progress = Column(JSON, nullable=False, default=list)
    open_work = Column(JSON, nullable=False, default=list)
    blockers = Column(JSON, nullable=False, default=list)
    decisions = Column(JSON, nullable=False, default=list)
    risks = Column(JSON, nullable=False, default=list)
    next_actions = Column(JSON, nullable=False, default=list)
    as_of = Column(DateTime(timezone=True), nullable=False, index=True)
    staleness_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class CheckpointModel(Base):
    __tablename__ = "executive_checkpoints"

    id = Column(String(64), primary_key=True, default=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    checkpoint_id = Column(String(64), unique=True, nullable=False, index=True)
    workflow_id = Column(String(128), nullable=False, index=True)
    goal_id = Column(String(128), nullable=True)
    state_payload = Column(JSON, nullable=False, default=dict)
    progress = Column(String(64), nullable=False, default="IN_PROGRESS")
    dependencies = Column(JSON, nullable=False, default=list)
    authorization = Column(JSON, nullable=False, default=dict)
    next_step = Column(JSON, nullable=False, default=dict)
    valid = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class NextActionModel(Base):
    __tablename__ = "next_actions"

    id = Column(String(64), primary_key=True, default=lambda: f"act_{uuid.uuid4().hex[:12]}")
    action_id = Column(String(64), unique=True, nullable=False, index=True)
    objective = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    dependencies = Column(JSON, nullable=False, default=list)
    authorization_status = Column(String(64), nullable=False, default="REQUIRED")
    confidence = Column(Float, nullable=False, default=0.8)
    status = Column(String(32), nullable=False, default="RECOMMENDED", index=True)
    project_id = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
