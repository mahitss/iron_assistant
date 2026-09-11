"""SQLAlchemy database models for Kairo Autonomous Goal Management & Self-Directed Mission Engine (Task 66)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class GoalModel(Base):
    """Persistent goal entity in relational storage."""

    __tablename__ = "mission_goals"

    goal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(String(64), default="USER", nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(128), default="user", nullable=False)
    stakeholders_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    urgency: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    constraints_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success_criteria_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    failure_conditions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dependencies_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    resources_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risk_level: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    authority_scope: Mapped[str] = mapped_column(String(64), default="EXECUTE_LOW_RISK", nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="DRAFT", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    __table_args__ = (
        Index("ix_mission_goals_tenant_status", "tenant_id", "status"),
        Index("ix_mission_goals_origin", "origin"),
    )


class MissionModel(Base):
    """Persistent mission execution record."""

    __tablename__ = "mission_records"

    mission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    goal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    authority_scope: Mapped[str] = mapped_column(String(64), default="EXECUTE_LOW_RISK", nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="DRAFT", nullable=False, index=True)
    health: Mapped[str] = mapped_column(String(64), default="ON_TRACK", nullable=False, index=True)
    active_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_versions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    budget_limits_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    budget_consumed_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checkpoints_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    blockers_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    __table_args__ = (
        Index("ix_mission_records_tenant_status", "tenant_id", "status"),
        Index("ix_mission_records_health", "health"),
    )


class MissionCheckpointModel(Base):
    """Persistent checkpoints recorded along mission trajectory."""

    __tablename__ = "mission_checkpoints"

    checkpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risks_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    next_steps_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    verification_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False, index=True
    )


class MissionBlockerModel(Base):
    """Persistent blocker records."""

    __tablename__ = "mission_blockers"

    blocker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    blocker_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DETECTED", nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MissionPostmortemModel(Base):
    """Persistent postmortem retrospectives."""

    __tablename__ = "mission_postmortems"

    postmortem_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    final_status: Mapped[str] = mapped_column(String(64), nullable=False)
    what_worked_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    what_failed_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    unexpected_events_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    planning_errors_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    resource_problems_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    agent_performance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    lessons_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MissionAuditRecordModel(Base):
    """Append-only cryptographic SHA-256 audit chain storage."""

    __tablename__ = "mission_audit_records"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    authority: Mapped[str] = mapped_column(String(64), default="EXECUTE_LOW_RISK", nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
