"""SQLAlchemy ORM models for Collective Intelligence & Swarm Reasoning Engine (Task 64)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

JSON_TYPE = JSONB().with_variant(Text, "sqlite")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SwarmSessionModel(Base):
    __tablename__ = "swarm_sessions"

    swarm_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    topology: Mapped[str] = mapped_column(String(32), default="STAR")
    status: Mapped[str] = mapped_column(String(32), default="INITIALIZING")
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    consensus_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc)


class SwarmTaskModel(Base):
    __tablename__ = "swarm_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    swarm_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    role_needed: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    is_critical_path: Mapped[bool] = mapped_column(Boolean, default=False)
    result_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class SwarmResultModel(Base):
    __tablename__ = "swarm_results"

    result_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    swarm_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class SwarmDisagreementModel(Base):
    __tablename__ = "swarm_disagreements"

    disagreement_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    swarm_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(32), default="DETECTED")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class SwarmMinorityReportModel(Base):
    __tablename__ = "swarm_minority_reports"

    minority_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    swarm_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dissenting_agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    dissenting_role: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.75)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class SwarmAuditRecordModel(Base):
    __tablename__ = "swarm_audit_records"

    sequence_number: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    previous_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="swarm_engine")
    swarm_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    details: Mapped[str] = mapped_column(Text, default="{}")
