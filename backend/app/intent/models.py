"""SQLAlchemy models for Kairo Unified Commands and Structured Intents (Task 35)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
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
