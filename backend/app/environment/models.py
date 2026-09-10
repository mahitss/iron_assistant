"""SQLAlchemy ORM models for Kairo Environmental Intelligence & Digital Twin Engine (Task 54)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DigitalTwinModel(Base):
    __tablename__ = "digital_twins"

    id = Column(String(64), primary_key=True, default=lambda: f"dtw_{uuid.uuid4().hex[:12]}")
    twin_id = Column(String(64), unique=True, nullable=False, index=True)
    scope = Column(String(64), nullable=False, default="SYSTEM")
    scope_id = Column(String(128), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    nodes = Column(JSON, nullable=False, default=dict)
    edges = Column(JSON, nullable=False, default=dict)
    health = Column(JSON, nullable=False, default=dict)
    changes = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=1.0)
    provenance = Column(JSON, nullable=False, default=dict)
    freshness = Column(String(64), nullable=False, default="FRESH")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_dtw_scope_idx", "scope", "scope_id"),
        Index("ix_dtw_timestamp_idx", "timestamp"),
    )


class EnvironmentNodeModel(Base):
    __tablename__ = "environment_nodes"

    id = Column(String(64), primary_key=True, default=lambda: f"enode_{uuid.uuid4().hex[:12]}")
    node_id = Column(String(128), unique=True, nullable=False, index=True)
    node_type = Column(String(64), nullable=False)
    canonical_id = Column(String(256), nullable=False, index=True)
    display_name = Column(String(256), nullable=False)
    node_metadata = Column(JSON, nullable=False, default=dict)
    scope = Column(String(64), nullable=False, default="SYSTEM")
    scope_id = Column(String(128), nullable=True)
    status = Column(String(64), nullable=False, default="UNKNOWN")
    first_seen = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    last_seen = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    provenance = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=1.0)

    __table_args__ = (
        Index("ix_enode_type_scope_idx", "node_type", "scope", "scope_id"),
        Index("ix_enode_last_seen_idx", "last_seen"),
    )


class EnvironmentEdgeModel(Base):
    __tablename__ = "environment_edges"

    id = Column(String(64), primary_key=True, default=lambda: f"eedge_{uuid.uuid4().hex[:12]}")
    edge_id = Column(String(128), unique=True, nullable=False, index=True)
    source = Column(String(128), nullable=False)
    relationship = Column(String(64), nullable=False)
    target = Column(String(128), nullable=False)
    confidence = Column(String(64), nullable=False, default="OBSERVED")
    provenance = Column(JSON, nullable=False, default=dict)
    valid_from = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(64), nullable=False, default="ACTIVE")

    __table_args__ = (
        Index("ix_eedge_src_rel_tgt_idx", "source", "relationship", "target"),
        Index("ix_eedge_status_idx", "status"),
    )


class EnvironmentDriftModel(Base):
    __tablename__ = "environment_drifts"

    id = Column(String(64), primary_key=True, default=lambda: f"edrift_{uuid.uuid4().hex[:12]}")
    drift_id = Column(String(64), unique=True, nullable=False, index=True)
    resource = Column(String(128), nullable=False, index=True)
    drift_type = Column(String(64), nullable=False)
    expected = Column(JSON, nullable=False, default=dict)
    actual = Column(JSON, nullable=False, default=dict)
    detected_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    severity = Column(String(64), nullable=False, default="MEDIUM")
    evidence = Column(JSON, nullable=False, default=dict)
    status = Column(String(64), nullable=False, default="DETECTED")

    __table_args__ = (
        Index("ix_edrift_type_status_idx", "drift_type", "status"),
    )


class EnvironmentChangeModel(Base):
    __tablename__ = "environment_changes"

    id = Column(String(64), primary_key=True, default=lambda: f"echange_{uuid.uuid4().hex[:12]}")
    change_id = Column(String(64), unique=True, nullable=False, index=True)
    resource = Column(String(128), nullable=False, index=True)
    change_type = Column(String(64), nullable=False)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    source = Column(String(128), nullable=False)
    significance = Column(String(64), nullable=False, default="LOW")
    confidence = Column(Float, nullable=False, default=1.0)
    verification = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_echange_ts_idx", "timestamp"),
    )


class EnvironmentIncidentModel(Base):
    __tablename__ = "environment_incidents"

    id = Column(String(64), primary_key=True, default=lambda: f"einc_{uuid.uuid4().hex[:12]}")
    incident_id = Column(String(64), unique=True, nullable=False, index=True)
    scope = Column(String(64), nullable=False, default="SYSTEM")
    scope_id = Column(String(128), nullable=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    severity = Column(String(64), nullable=False, default="MEDIUM")
    symptoms = Column(JSON, nullable=False, default=list)
    affected_resources = Column(JSON, nullable=False, default=list)
    suspected_cause = Column(String(256), nullable=True)
    root_cause = Column(String(256), nullable=True)
    evidence = Column(JSON, nullable=False, default=dict)
    status = Column(String(64), nullable=False, default="DETECTED")
    timeline = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        Index("ix_einc_scope_idx", "scope", "scope_id"),
        Index("ix_einc_status_idx", "status"),
    )


class EnvironmentSnapshotModel(Base):
    __tablename__ = "environment_snapshots"

    id = Column(String(64), primary_key=True, default=lambda: f"esnap_{uuid.uuid4().hex[:12]}")
    snapshot_id = Column(String(64), unique=True, nullable=False, index=True)
    scope = Column(String(64), nullable=False, default="SYSTEM")
    scope_id = Column(String(128), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    nodes = Column(JSON, nullable=False, default=list)
    edges = Column(JSON, nullable=False, default=list)
    health_summary = Column(JSON, nullable=False, default=dict)
    freshness = Column(String(64), nullable=False, default="FRESH")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_esnap_scope_idx", "scope", "scope_id"),
        Index("ix_esnap_ts_idx", "timestamp"),
    )
