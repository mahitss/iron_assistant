"""SQLAlchemy ORM models for Task 96 Swarm Orchestration and Agent Identity."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, JSON, String, Text
from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(UTC)


class AgentIdentityModel(Base):
    """Relational persistence of an autonomous agent instance."""
    __tablename__ = "agent_identities"

    agent_id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    role = Column(String(32), nullable=False, index=True)
    parent_agent_id = Column(String(64), nullable=True, index=True)
    task_id = Column(String(64), nullable=True)

    capability_scope_json = Column(JSON, nullable=False, default=list)
    context_scope = Column(String(64), default="PRIVATE_AGENT_CONTEXT")
    resource_scope_json = Column(JSON, nullable=False, default=dict)

    lifecycle_state = Column(String(32), nullable=False, default="CREATED")
    lifecycle_reason = Column(Text, default="")
    trust_score = Column(Float, default=0.85)

    created_at = Column(DateTime(timezone=True), default=_now_utc)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc)


class AgentTaskModel(Base):
    """Relational persistence of delegated agent tasks."""
    __tablename__ = "agent_orchestration_tasks"

    task_id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    parent_task_id = Column(String(64), nullable=True, index=True)
    root_task_id = Column(String(64), nullable=True)

    objective = Column(Text, nullable=False)
    role_needed = Column(String(32), nullable=False)
    assigned_agent_id = Column(String(64), nullable=True, index=True)
    priority = Column(String(16), default="NORMAL")

    dependencies_json = Column(JSON, nullable=False, default=list)
    dependency_state = Column(String(32), default="READY")

    required_capabilities_json = Column(JSON, nullable=False, default=list)
    resource_budget_json = Column(JSON, nullable=False, default=dict)

    status = Column(String(32), default="PENDING")
    created_at = Column(DateTime(timezone=True), default=_now_utc)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AgentMessageModel(Base):
    """Relational audit trail of inter-agent typed messages."""
    __tablename__ = "agent_messages"

    message_id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    sender_id = Column(String(64), nullable=False, index=True)
    recipient_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True)

    message_type = Column(String(32), nullable=False)
    payload_json = Column(JSON, nullable=False, default=dict)
    provenance_json = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), default=_now_utc)
