"""SQLAlchemy models for Kairo Identity, Session Continuity, Presence, and Handoff (Task 33)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import DateTime, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IdentitySessionModel(Base):
    """Relational store for authenticated interaction sessions."""

    __tablename__ = "identity_sessions"

    session_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"sess_{uuid.uuid4().hex[:16]}",
        comment="Unique session identifier",
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Owner user ID (strict tenant boundary)",
    )
    client_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Client type: WEB, DESKTOP, MOBILE, VOICE, API, LOCAL_COMPANION",
    )
    device_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Optional bound device ID",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
        comment="Lifecycle status: ACTIVE, EXPIRED, REVOKED",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_identity_sessions_user_status", "user_id", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "client_type": self.client_type,
            "device_id": self.device_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "metadata": self.metadata_json or {},
        }


class IdentityPresenceModel(Base):
    """Real-time application-level interface presence tracking."""

    __tablename__ = "identity_presence"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"pres_{uuid.uuid4().hex[:16]}",
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    device_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    interface: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
        comment="ACTIVE, IDLE, DISCONNECTED",
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "device_id": self.device_id,
            "interface": self.interface,
            "state": self.state,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class HandoffContextModel(Base):
    """Scoped, bounded, single-use cross-interface handoff state."""

    __tablename__ = "handoff_contexts"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"ho_{uuid.uuid4().hex[:16]}",
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    source_session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    target_session_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    target_device_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    task_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    relevant_context: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_session_id": self.source_session_id,
            "target_session_id": self.target_session_id,
            "target_device_id": self.target_device_id,
            "conversation_id": self.conversation_id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "relevant_context": self.relevant_context,
            "consumed": self.consumed_at is not None,
            "consumed_at": self.consumed_at.isoformat() if self.consumed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
