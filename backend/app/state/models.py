"""SQLAlchemy models for Kairo Unified Data & State Fabric (Task 39)."""

from datetime import UTC, datetime
from typing import Any
from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class StateRecordModel(Base):
    """Authoritative or derived state record stored in the fabric (Spec 10)."""
    __tablename__ = "state_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="AUTHORITATIVE", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    data_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_domain: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("domain", "resource_type", "resource_id", name="uq_state_record_domain_resource"),
    )


class StateChangelogModel(Base):
    """Durable append-only change stream for state mutations (Spec 22)."""
    __tablename__ = "state_changelog"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    service: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    changes_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)


class StateSnapshotModel(Base):
    """Snapshot of a projection for fast recovery and roll-forward (Spec 30)."""
    __tablename__ = "state_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    projection_identifier: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)


class StateLockModel(Base):
    """Distributed lock lease with mandatory TTL and fencing token (Spec 58-60)."""
    __tablename__ = "state_locks"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    fencing_token: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class StateQuarantineModel(Base):
    """Isolated corrupt projections, bad cache items, or impossible states (Spec 138-140)."""
    __tablename__ = "state_quarantine"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    quarantined_by: Mapped[str] = mapped_column(String(64), nullable=False)
    quarantined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
