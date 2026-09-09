"""
SQLAlchemy database models for Event Store, Transactional Outbox, and Dead-Letter Queue.
"""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    JSON,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class EventRecord(Base):
    """Durable persistence for emitted domain events (Section 22 & 23)."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_version: Mapped[str] = mapped_column(String(16), default="v1", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PUBLISHED", nullable=False)

    __table_args__ = (
        Index("ix_events_type_timestamp", "event_type", "timestamp"),
        Index("ix_events_user_timestamp", "user_id", "timestamp"),
        Index("ix_events_correlation", "correlation_id"),
    )

    def __repr__(self) -> str:
        return f"<EventRecord(id='{self.id}', type='{self.event_type}', source='{self.source}')>"


class EventOutboxRecord(Base):
    """Transactional outbox table guaranteeing at-least-once publishing (Section 52 & 53)."""

    __tablename__ = "event_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)
    event_data_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_event_outbox_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<EventOutboxRecord(id='{self.id}', event_id='{self.event_id}', status='{self.status}')>"


class DeadLetterEventRecord(Base):
    """Observable dead-letter storage for repeatedly failing events (Section 17 & 18)."""

    __tablename__ = "dead_letter_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    handler_name: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    replay_safety: Mapped[str] = mapped_column(String(32), default="REPLAY_REQUIRES_REVIEW", nullable=False)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replayed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<DeadLetterEventRecord(id='{self.id}', event_id='{self.event_id}', handler='{self.handler_name}')>"
