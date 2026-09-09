"""SQLAlchemy models for Kairo Unified Commands, Structured Intents, Goals, and Motivation (Tasks 35 & 48)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CommandModel(Base):
    """Stores incoming normalized user commands across all interfaces (Web, Desktop, Voice, API)."""

    __tablename__ = "unified_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    source_interface: Mapped[str] = mapped_column(String(32), default="WEB", nullable=False)
    project_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    intents: Mapped[list["IntentModel"]] = relationship(
        "IntentModel",
        back_populates="command",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_unified_commands_user_created", "user_id", "created_at"),
    )


class IntentModel(Base):
    """Stores validated structured intents extracted from commands with ambiguity and risk metadata."""

    __tablename__ = "unified_intents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    command_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("unified_commands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    entities_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    references_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    constraints_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    requested_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ambiguity_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    risk: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="READY", nullable=False)
    next_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    command: Mapped["CommandModel"] = relationship("CommandModel", back_populates="intents")

    __table_args__ = (
        Index("ix_unified_intents_user_type", "user_id", "type"),
        Index("ix_unified_intents_user_created", "user_id", "created_at"),
    )


class GoalModel(Base):
    """Persisted user desired outcome distinct from specific execution tasks (Spec 9, 10)."""

    __tablename__ = "user_goals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    desired_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    success_criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    scope_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    constraints_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str] = mapped_column(String(64), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ObjectiveModel(Base):
    """Measurable sub-outcome contributing to an overarching user goal (Spec 11-14)."""

    __tablename__ = "intent_objectives"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    goal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_metric: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssumptionModel(Base):
    """Transparently tracked operational assumption (Spec 50-54)."""

    __tablename__ = "intent_assumptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="INFERRED", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    impact: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AmbiguityRecordModel(Base):
    """Detected ambiguity with candidates and resolution state (Spec 55-57)."""

    __tablename__ = "intent_ambiguities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    candidates: Mapped[list[Any]] = mapped_column(JSON, default=list)
    impact: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    level: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    resolution: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="UNRESOLVED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ClarificationModel(Base):
    """Targeted clarification query requiring user feedback before consequential actions (Spec 58-62)."""

    __tablename__ = "intent_clarifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_decision: Mapped[str] = mapped_column(String(256), nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_if_any: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class MotivationModel(Base):
    """Non-psychological functional motivation signal (Spec 76-80)."""

    __tablename__ = "intent_motivations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentGraphModel(Base):
    """Directed Acyclic Graph linking Intent -> Goal -> Objectives -> Constraints -> Tasks -> Outcomes (Spec 74)."""

    __tablename__ = "intent_graphs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    goal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
