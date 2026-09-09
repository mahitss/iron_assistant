"""SQLAlchemy data models for Kairo Device Management and Local Companion Runtime."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.db.session import Base
from sqlalchemy import JSON, Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class DeviceModel(Base):
    """Authoritative record of a registered user device executing the Kairo Local Companion."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"dev_{uuid.uuid4().hex[:16]}",
        comment="Unique device identifier (device_id)",
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Owner user identifier (strict tenant boundary)",
    )
    device_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Human-readable device name (e.g. 'My Workstation')",
    )
    os_name: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Operating system (windows, darwin, linux)",
    )
    os_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="unknown",
        comment="OS kernel or build version",
    )
    companion_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.1.0",
        comment="Installed Kairo Local Companion version",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        comment="Device lifecycle state: PENDING, ACTIVE, REVOKED, DISABLED",
    )
    public_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Base64 or PEM encoded public key for signature verification",
    )
    credentials_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Cryptographic hash of device token for authentication",
    )

    # Granular capability gates (default OFF)
    computer_control_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether computer control is permitted on this device (default OFF)",
    )
    voice_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether local microphone/wake-word is permitted (default OFF)",
    )
    camera_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether local camera capture is permitted (default OFF)",
    )
    filesystem_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether sandboxed filesystem access is permitted (default OFF)",
    )
    allowed_paths: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="Strict filesystem allowlist directory paths for this device",
    )

    # Task 33: Device Trust, Pairing & Declared Capabilities
    trust_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="UNTRUSTED",
        comment="Explicit device trust: UNTRUSTED, PENDING, TRUSTED, REVOKED",
    )
    client_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="LOCAL_COMPANION",
        comment="Client interface type: DESKTOP, MOBILE, LOCAL_COMPANION, etc.",
    )
    pairing_code_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Hashed single-use pairing code",
    )
    pairing_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiration timestamp for pending pairing code",
    )
    trust_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiration timestamp for trusted device status",
    )
    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="Declared hardware capabilities: SCREEN, MICROPHONE, CAMERA, KEYBOARD, MOUSE, etc.",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when device was revoked",
    )

    __table_args__ = (
        Index("ix_devices_user_id_status", "user_id", "status"),
        Index("ix_devices_trust_status", "trust_status"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to safe dictionary representation."""
        return {
            "device_id": self.id,
            "user_id": self.user_id,
            "device_name": self.device_name,
            "client_type": self.client_type,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "companion_version": self.companion_version,
            "status": self.status,
            "trust_status": self.trust_status,
            "capabilities": {
                "computer_control": self.computer_control_enabled,
                "voice": self.voice_enabled,
                "camera": self.camera_enabled,
                "filesystem": self.filesystem_enabled,
            },
            "declared_capabilities": self.capabilities,
            "allowed_paths": self.allowed_paths,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "trust_expires_at": self.trust_expires_at.isoformat() if self.trust_expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
