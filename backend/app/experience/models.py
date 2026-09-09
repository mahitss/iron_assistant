"""SQLAlchemy database models for Kairo Long-Term Experience and Learning."""

import uuid
from datetime import UTC, datetime
from typing import Any

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
    """Generate timezone-aware UTC current timestamp."""
    return datetime.now(UTC)


class ExperienceRecord(Base):
    """Stores observed task outcomes, explicit user corrections, and evaluation signals."""

    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PROJECT", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_experiences_user_status", "user_id", "status"),
        Index("ix_experiences_project_type", "project_id", "type"),
        Index("ix_experiences_user_scope", "user_id", "scope"),
    )

    def __repr__(self) -> str:
        return f"<ExperienceRecord(id='{self.id}', type='{self.type}', status='{self.status}')>"


class PreferenceRecord(Base):
    """Stores validated user and project preferences."""

    __tablename__ = "preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PROJECT", index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="USER_EXPLICIT", nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_preferences_user_key_scope", "user_id", "key", "scope"),
    )

    def __repr__(self) -> str:
        return f"<PreferenceRecord(id='{self.id}', key='{self.key}', scope='{self.scope}')>"


class LearningCandidateRecord(Base):
    """Proposed improvements awaiting engineering or benchmark review."""

    __tablename__ = "learning_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_event: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    proposed_change: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="GLOBAL", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<LearningCandidateRecord(id='{self.id}', status='{self.status}')>"


class UserFeedbackRecord(Base):
    """Raw user ratings, thumbs up/down, and interaction corrections."""

    __tablename__ = "user_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    def __repr__(self) -> str:
        return f"<UserFeedbackRecord(id='{self.id}', type='{self.feedback_type}')>"
