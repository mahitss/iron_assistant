"""SQLAlchemy Database Models for Kairo Perception & Environmental Awareness Engine (Task 46)."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PerceptionSourceModel(Base):
    """Persistent storage for registered environmental perception sources (Spec 2)."""

    __tablename__ = "perception_sources"

    id = Column(String(64), primary_key=True, default=lambda: f"src_{uuid.uuid4().hex[:12]}")
    type = Column(String(32), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    scope_data = Column(JSON, nullable=False, default=dict)
    capabilities = Column(JSON, nullable=False, default=list)
    reliability = Column(Float, nullable=False, default=1.0)
    status = Column(String(32), nullable=False, default="HEALTHY", index=True)
    privacy_level = Column(String(32), nullable=False, default="INTERNAL")
    last_seen = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class PerceptionObservationModel(Base):
    """Persistent store for empirical observations with provenance and freshness (Spec 6, 7)."""

    __tablename__ = "perception_observations"

    id = Column(String(64), primary_key=True, default=lambda: f"obs_{uuid.uuid4().hex[:12]}")
    source_id = Column(String(64), ForeignKey("perception_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(32), nullable=False)
    subject = Column(String(256), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)
    payload_reference = Column(String(256), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    correlation_id = Column(String(64), nullable=True, index=True)
    scope_data = Column(JSON, nullable=False, default=dict)
    provenance_data = Column(JSON, nullable=False, default=dict)
    data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_perception_obs_subj_time", "subject", "observed_at"),
    )


class PerceptionChangeEventModel(Base):
    """Persistent ledger of environmental changes and evaluated significance (Spec 79, 80)."""

    __tablename__ = "perception_change_events"

    id = Column(String(64), primary_key=True, default=lambda: f"chg_{uuid.uuid4().hex[:12]}")
    subject = Column(String(256), nullable=False, index=True)
    change_type = Column(String(32), nullable=False, index=True)
    significance = Column(String(32), nullable=False, index=True)
    environment = Column(String(32), nullable=False, default="DEVELOPMENT", index=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=False, default=dict)
    source_id = Column(String(64), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)


class PerceptionSnapshotModel(Base):
    """Versioned environmental state snapshots (Spec 31, 32)."""

    __tablename__ = "perception_snapshots"

    id = Column(String(64), primary_key=True, default=lambda: f"snap_{uuid.uuid4().hex[:12]}")
    version = Column(Integer, nullable=False)
    environment = Column(String(32), nullable=False, index=True)
    is_atomic = Column(Boolean, nullable=False, default=True)
    devices = Column(JSON, nullable=False, default=dict)
    apps = Column(JSON, nullable=False, default=dict)
    services = Column(JSON, nullable=False, default=dict)
    repositories = Column(JSON, nullable=False, default=dict)
    deployments = Column(JSON, nullable=False, default=dict)
    tasks = Column(JSON, nullable=False, default=dict)
    agents = Column(JSON, nullable=False, default=dict)
    missing_sources = Column(JSON, nullable=False, default=list)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_perception_snap_env_ver", "environment", "version", unique=True),
    )


class PerceptionSituationModel(Base):
    """Synthesized situational awareness representations (Spec 100-106)."""

    __tablename__ = "perception_situations"

    id = Column(String(64), primary_key=True, default=lambda: f"sit_{uuid.uuid4().hex[:12]}")
    version = Column(Integer, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    scope_data = Column(JSON, nullable=False, default=dict)
    observed_facts = Column(JSON, nullable=False, default=list)
    inferences = Column(JSON, nullable=False, default=list)
    changes = Column(JSON, nullable=False, default=list)
    anomalies = Column(JSON, nullable=False, default=list)
    risks = Column(JSON, nullable=False, default=list)
    uncertainties = Column(JSON, nullable=False, default=list)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)
