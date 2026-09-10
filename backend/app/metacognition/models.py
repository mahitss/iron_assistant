"""SQLAlchemy ORM models for Kairo Self-Modeling & Metacognition Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import JSON, Column, DateTime, Float, String, Text
from app.db.session import Base


class SelfModelSnapshotModel(Base):
    __tablename__ = "metacog_self_model_snapshots"

    id = Column(String(64), primary_key=True)
    version = Column(String(32), nullable=False, default="1.0.0")
    state_json = Column(JSON, nullable=False, default=dict)
    capabilities_json = Column(JSON, nullable=False, default=dict)
    limitations_json = Column(JSON, nullable=False, default=list)
    resource_json = Column(JSON, nullable=False, default=dict)
    policy_json = Column(JSON, nullable=False, default=dict)
    user_id = Column(String(64), nullable=False, index=True, default="default_user")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)


class LimitationModel(Base):
    __tablename__ = "metacog_limitations"

    id = Column(String(64), primary_key=True)
    category = Column(String(32), nullable=False, index=True)
    description = Column(Text, nullable=False)
    scope = Column(String(32), nullable=False, default="GLOBAL")
    severity = Column(String(32), nullable=False, default="MEDIUM")
    source = Column(String(64), nullable=False, default="SYSTEM")
    status = Column(String(32), nullable=False, default="ACTIVE")
    user_id = Column(String(64), nullable=False, index=True, default="default_user")
    detected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class FailureModel(Base):
    __tablename__ = "metacog_failures"

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), nullable=True, index=True)
    action = Column(String(128), nullable=False)
    failure_type = Column(String(32), nullable=False)
    cause = Column(Text, nullable=False)
    evidence_json = Column(JSON, nullable=False, default=list)
    recoverability = Column(String(32), nullable=False, default="RECOVERABLE")
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    user_id = Column(String(64), nullable=False, index=True, default="default_user")


class ReflectionModel(Base):
    __tablename__ = "metacog_reflections"

    id = Column(String(64), primary_key=True)
    goal_id = Column(String(64), nullable=True, index=True)
    task_id = Column(String(64), nullable=True)
    summary_json = Column(JSON, nullable=False, default=dict)
    lessons_json = Column(JSON, nullable=False, default=list)
    corrections_json = Column(JSON, nullable=False, default=list)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    user_id = Column(String(64), nullable=False, index=True, default="default_user")
