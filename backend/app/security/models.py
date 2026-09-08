"""SQLAlchemy models for Security Center: sessions, approvals, audit trail, and capabilities."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    """Generate timezone-aware UTC current timestamp."""
    return datetime.now(UTC)


class SecuritySession(Base):
    """Represents an active security context for a user or client."""

    __tablename__ = "security_sessions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"sec_sess_{uuid.uuid4().hex}"
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (Index("ix_security_sessions_user_active", "user_id", "is_active"),)

    def __repr__(self) -> str:
        return f"<SecuritySession(id='{self.id}', user_id='{self.user_id}', is_active={self.is_active})>"


class SecurityApprovalRequest(Base):
    """Represents a human-in-the-loop approval gate for any restricted tool/action."""

    __tablename__ = "security_approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False)
    arguments_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    action_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), index=True, default="pending", nullable=False
    )  # pending, approved, denied, expired, cancelled
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_security_approvals_user_status", "user_id", "status"),
        Index("ix_security_approvals_fingerprint_status", "action_fingerprint", "status"),
    )

    def __repr__(self) -> str:
        return f"<SecurityApprovalRequest(id='{self.id}', tool='{self.tool_name}', status='{self.status}')>"


class SecurityAuditEvent(Base):
    """Immutable append-only audit trail event tracking security-sensitive actions."""

    __tablename__ = "security_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_security_audit_user_timestamp", "user_id", "timestamp"),
        Index("ix_security_audit_user_event", "user_id", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<SecurityAuditEvent(id='{self.id}', type='{self.event_type}', tool='{self.tool_name}')>"


class UserCapabilities(Base):
    """User-level capability controls and feature gates."""

    __tablename__ = "user_capabilities"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    web_research: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    browser: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    voice: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vision: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    computer_control: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # OFF by default!
    developer_tools: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    automation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def to_dict(self) -> dict[str, bool]:
        """Convert capabilities to dictionary."""
        return {
            "web_research": self.web_research,
            "browser": self.browser,
            "voice": self.voice,
            "vision": self.vision,
            "computer_control": self.computer_control,
            "developer_tools": self.developer_tools,
            "automation": self.automation,
        }

    def __repr__(self) -> str:
        return f"<UserCapabilities(user_id='{self.user_id}', computer_control={self.computer_control})>"
