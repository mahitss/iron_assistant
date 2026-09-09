"""SQLAlchemy models for Kairo Social and Communication Intelligence Engine (Task 49)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ChannelModel(Base):
    """Stores communication channel authorization, capabilities, and quiet hours."""

    __tablename__ = "communication_channels"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(16), nullable=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ThreadModel(Base):
    """Stores conversation threads grouped across single or multi-channel communications."""

    __tablename__ = "communication_threads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    importance: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    participants_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class MessageModel(Base):
    """Stores normalized communication messages across email, chat, meetings, and voice."""

    __tablename__ = "communication_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sender_identity: Mapped[str] = mapped_column(String(256), nullable=False)
    recipients_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    direction: Mapped[str] = mapped_column(String(32), default="INBOUND", nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DELIVERED", nullable=False)
    provenance_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    privacy_scope: Mapped[str] = mapped_column(String(32), default="PRIVATE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RelationshipModel(Base):
    """Stores safe relationship contexts (teammate, collaborator, client) without social profiling."""

    __tablename__ = "communication_relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    participant_identity: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(32), default="UNKNOWN", nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    communication_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    provenance_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommitmentModel(Base):
    """Stores explicit grounded commitments extracted from communications."""

    __tablename__ = "communication_commitments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class FollowUpModel(Base):
    """Stores automated and user-requested follow-ups with loop prevention bounds."""

    __tablename__ = "communication_followups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(32), default="NO_RESPONSE", nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action_statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class DraftModel(Base):
    """Stores draft messages under review, strictly separated from sent messages."""

    __tablename__ = "communication_drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recipients_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(String(32), default="FORMAL", nullable=False)
    intent_type: Mapped[str] = mapped_column(String(32), default="REQUEST", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False, index=True)
    source_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    provenance_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
