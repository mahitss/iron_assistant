"""SQLAlchemy ORM models for Task 93: KAIRO Autonomous System State Graph & Self-Modeling.

Provides durable, immutable point-in-time snapshots, state deltas, and startup reconciliations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_hex(prefix: str, length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


class SystemStateSnapshotModel(Base):
    """Immutable point-in-time snapshot of Kairo's operational system state."""

    __tablename__ = "system_state_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("snap"))
    snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(32), server_default="v1", nullable=False)
    system_version: Mapped[str] = mapped_column(String(32), server_default="0.93.0", nullable=False)
    source_event_watermark: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    state_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    edge_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    entities_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    edges_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_sys_snap_hash", "state_hash"),
        Index("ix_sys_snap_created", "created_at"),
        Index("ix_sys_snap_watermark", "source_event_watermark"),
    )


class SystemStateDeltaModel(Base):
    """Recorded operational state delta between two snapshots."""

    __tablename__ = "system_state_deltas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("delta"))
    delta_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    from_snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    to_snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    delta_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    epistemic_status: Mapped[str] = mapped_column(String(32), server_default="OBSERVED", nullable=False)
    affected_tasks: Mapped[list[str]] = mapped_column(JSON, default=list)
    affected_workflows: Mapped[list[str]] = mapped_column(JSON, default=list)
    affected_goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    affected_dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_sys_delta_from_to", "from_snapshot_id", "to_snapshot_id"),
        Index("ix_sys_delta_entity", "entity_id", "delta_type"),
        Index("ix_sys_delta_detected", "detected_at"),
    )


class SystemStateReconciliationModel(Base):
    """Audit log of startup reconciliation and orphaned state repair."""

    __tablename__ = "system_state_reconciliations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("reconcile"))
    reconciliation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    watermark_start: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    watermark_end: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    repaired_entities: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    orphaned_entities: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    stale_entities: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="COMPLETED", nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_sys_reconcile_created", "created_at"),
        Index("ix_sys_reconcile_status", "status"),
    )
