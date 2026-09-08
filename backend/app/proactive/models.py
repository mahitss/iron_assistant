"""SQLAlchemy declarative models for proactive insights, settings, and web monitoring."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
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


class ProactiveInsight(Base):
    """Represents a prioritized, actionable insight surfaced proactively by Kairo."""

    __tablename__ = "proactive_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), index=True, default="MEDIUM", nullable=False)
    actionability: Mapped[str] = mapped_column(String(32), default="INFORMATIONAL", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), index=True, default="new", nullable=False
    )  # new, delivered, read, dismissed, expired
    action_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_proactive_insights_user_status", "user_id", "status"),
        Index("ix_proactive_insights_user_priority", "user_id", "priority"),
        Index("ix_proactive_insights_user_fingerprint", "user_id", "fingerprint"),
    )

    def __repr__(self) -> str:
        return f"<ProactiveInsight(id='{self.id}', title='{self.title}', priority='{self.priority}')>"


class UserProactiveSettings(Base):
    """User preferences for proactive notifications, priority thresholds, and quiet hours."""

    __tablename__ = "proactive_settings"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proactive_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_workflow_failure: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_ci_failure: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_web_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    minimum_priority: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(16), default="22:00", nullable=False)
    quiet_hours_end: Mapped[str] = mapped_column(String(16), default="08:00", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserProactiveSettings(user_id='{self.user_id}', enabled={self.proactive_enabled})>"


class WebMonitor(Base):
    """Monitored web URL configuration for change detection."""

    __tablename__ = "web_monitors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    content_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_web_monitors_user_enabled", "user_id", "enabled"),)

    def __repr__(self) -> str:
        return f"<WebMonitor(id='{self.id}', name='{self.name}', enabled={self.enabled})>"
