"""SQLAlchemy declarative models for Kairo Unified Notification & Alerting Layer (Task 34)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class NotificationModel(Base):
    """Authoritative notification record representing communication to the user."""

    __tablename__ = "unified_notifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL", index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    actions: Mapped[list["NotificationActionModel"]] = relationship(
        "NotificationActionModel",
        back_populates="notification",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    deliveries: Mapped[list["NotificationDeliveryModel"]] = relationship(
        "NotificationDeliveryModel",
        back_populates="notification",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_notifications_user_status", "user_id", "status"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )


class NotificationActionModel(Base):
    """Interactive, typed action bound to an active notification."""

    __tablename__ = "notification_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    notification_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("unified_notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notification: Mapped["NotificationModel"] = relationship("NotificationModel", back_populates="actions")


class NotificationDeliveryModel(Base):
    """Delivery record for a notification across distinct channels and devices."""

    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    notification_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("unified_notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    notification: Mapped["NotificationModel"] = relationship("NotificationModel", back_populates="deliveries")


class NotificationPreferenceModel(Base):
    """User-scoped delivery, channel, quiet hours, and digest preferences."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=lambda: ["WEB"])
    type_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(8), nullable=False, default="22:00")
    quiet_hours_end: Mapped[str] = mapped_column(String(8), nullable=False, default="08:00")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    digest_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    digest_frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="daily")
    grouping_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_priority: Mapped[str] = mapped_column(String(16), nullable=False, default="LOW")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
