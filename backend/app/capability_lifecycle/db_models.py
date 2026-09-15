"""SQLAlchemy entities for capability lifecycle, immutable versions, events, and rollouts (Task 91 Phase 21)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CapabilityEntity(Base):
    """Persistent storage for registered capability metadata and lifecycle status."""

    __tablename__ = "capabilities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"cap_{uuid.uuid4().hex[:12]}")
    capability_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    capability_type: Mapped[str] = mapped_column(String(32), default="TOOL", nullable=False)
    owner_source: Mapped[str] = mapped_column(String(128), default="core.kairo", nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)

    # Fingerprints
    contract_fingerprint: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    implementation_fingerprint: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    composite_fingerprint: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    # State & Classification
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="DISCOVERED", index=True, nullable=False)
    health_state: Mapped[str] = mapped_column(String(32), default="UNKNOWN", nullable=False)
    security_classification: Mapped[str] = mapped_column(String(32), default="INTERNAL", nullable=False)

    # Serialized schemas & configurations
    parameters_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_schema: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    dependencies_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    resource_profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    reliability_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Active & Canary pointer
    active_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    canary_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_capabilities_type_state", "capability_type", "lifecycle_state"),
    )


class CapabilityVersionEntity(Base):
    """Immutable version history for capabilities."""

    __tablename__ = "capability_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"ver_{uuid.uuid4().hex[:12]}")
    capability_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    version_str: Mapped[str] = mapped_column(String(32), nullable=False)
    major: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    patch: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    contract_fingerprint: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    implementation_fingerprint: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    dependency_fingerprint: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_capability_versions_cap_ver", "capability_id", "version_str", unique=True),
    )


class CapabilityLifecycleEventEntity(Base):
    """Audit trail of all capability state machine transitions."""

    __tablename__ = "capability_lifecycle_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"ev_{uuid.uuid4().hex[:12]}")
    capability_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    safety_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class CapabilityRolloutEntity(Base):
    """Active and historical records of canary rollouts."""

    __tablename__ = "capability_rollouts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"roll_{uuid.uuid4().hex[:12]}")
    capability_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_version: Mapped[str] = mapped_column(String(32), nullable=False)
    current_percent: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    workloads_routed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_encountered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="INACTIVE", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
