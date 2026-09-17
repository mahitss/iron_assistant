"""SQLAlchemy models for KAIRO World-State Reconstruction, Snapshots, Observations, Drift & Conflict storage (Task 98, Phase 39)."""

from datetime import UTC, datetime
from typing import Any
import uuid

import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid(prefix: str = "st") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class WorldStateSnapshotModel(Base):
    """Immutable persistent world-state reference snapshots."""

    __tablename__ = "world_state_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("snap"))
    scope: Mapped[str] = mapped_column(String(32), default="SYSTEM", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    certainty: Mapped[str] = mapped_column(String(32), default="KNOWN", nullable=False)
    freshness: Mapped[str] = mapped_column(String(32), default="FRESH", nullable=False)
    drift_status: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entities_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_world_state_snapshots_scope_created", "scope", "created_at"),
    )


class StateObservationModel(Base):
    """Persistent audit storage of normalized state observations."""

    __tablename__ = "state_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("obs"))
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    observed_value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    certainty: Mapped[str] = mapped_column(String(32), default="KNOWN", nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), default="INTERNAL", nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="SYSTEM", nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_state_obs_entity_time", "entity_id", "observed_at"),
    )


class StateDriftRecordModel(Base):
    """Persistent drift events and reality discrepancies."""

    __tablename__ = "state_drift_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("drift"))
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), default="SYSTEM", nullable=False, index=True)
    drift_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(64), default="ACTIONABLE_DRIFT", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DETECTED", nullable=False, index=True)
    expected_value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    actual_value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    deviation_magnitude: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    causal_status: Mapped[str] = mapped_column(String(64), default="UNKNOWN", nullable=False)
    attributed_source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attributed_source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_state_drift_entity_severity", "entity_id", "severity"),
    )


class StateConflictRecordModel(Base):
    """Dialectic disagreements between multi-source observations."""

    __tablename__ = "state_conflict_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("conf"))
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attribute_name: Mapped[str] = mapped_column(String(64), nullable=False)
    resolution_state: Mapped[str] = mapped_column(String(32), default="UNRESOLVED", nullable=False, index=True)
    resolved_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RevalidationCandidateModel(Base):
    """Revalidation queue triggered by state mutations or drift."""

    __tablename__ = "revalidation_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("rev"))
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    drift_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
