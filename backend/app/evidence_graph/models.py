"""SQLAlchemy persistence models for Task 117:
Kairo Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine.
Tables use _t117 suffix for strict isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class EvidenceGraphNodeModel(Base):
    """Persistent graph node entity."""

    __tablename__ = "evidence_graph_nodes_t117"

    node_id = Column(String(64), primary_key=True)
    node_type = Column(String(32), nullable=False, index=True)
    source_system = Column(String(64), nullable=False, default="generic", index=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    temporal_scope_json = Column(JSON, nullable=False, default=dict)
    lifecycle_status = Column(String(32), nullable=False, default="ACTIVE", index=True)
    provenance_status = Column(String(32), nullable=False, default="UNVERIFIED", index=True)
    freshness_state = Column(String(32), nullable=False, default="FRESH", index=True)
    integrity_state = Column(String(32), nullable=False, default="INTACT", index=True)
    payload_json = Column(JSON, nullable=False, default=dict)
    content_hash = Column(String(64), nullable=False, default="", index=True)

    # Relationships
    outgoing_edges = relationship(
        "EvidenceGraphEdgeModel",
        foreign_keys="EvidenceGraphEdgeModel.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges = relationship(
        "EvidenceGraphEdgeModel",
        foreign_keys="EvidenceGraphEdgeModel.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "EvidenceGraphNodeVersionModel",
        back_populates="node",
        cascade="all, delete-orphan",
    )


class EvidenceGraphEdgeModel(Base):
    """Explicitly typed directed relationship with provenance metadata."""

    __tablename__ = "evidence_graph_edges_t117"

    edge_id = Column(String(64), primary_key=True)
    source_node_id = Column(
        String(64),
        ForeignKey("evidence_graph_nodes_t117.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id = Column(
        String(64),
        ForeignKey("evidence_graph_nodes_t117.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type = Column(String(32), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=1.0)
    provenance_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    discovered_at = Column(DateTime(timezone=True), nullable=True)
    source_system = Column(String(64), nullable=False, default="generic")
    actor_component = Column(String(64), nullable=False, default="system")
    evidence_references_json = Column(JSON, nullable=False, default=list)
    derivation_method = Column(String(64), nullable=False, default="DIRECT")
    verification_status = Column(String(32), nullable=False, default="UNVERIFIED")
    supersession_json = Column(JSON, nullable=True)
    correction_json = Column(JSON, nullable=True)
    scope_json = Column(JSON, nullable=False, default=dict)

    # Relationships
    source_node = relationship(
        "EvidenceGraphNodeModel",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
    )
    target_node = relationship(
        "EvidenceGraphNodeModel",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
    )
    versions = relationship(
        "EvidenceGraphEdgeVersionModel",
        back_populates="edge",
        cascade="all, delete-orphan",
    )


class EvidenceGraphNodeVersionModel(Base):
    """Immutable node historical version."""

    __tablename__ = "evidence_graph_node_versions_t117"

    version_id = Column(String(64), primary_key=True)
    node_id = Column(
        String(64),
        ForeignKey("evidence_graph_nodes_t117.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    node_type = Column(String(32), nullable=False)
    payload_json = Column(JSON, nullable=False, default=dict)
    content_hash = Column(String(64), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    supersedes_version = Column(Integer, nullable=True)

    node = relationship("EvidenceGraphNodeModel", back_populates="versions")


class EvidenceGraphEdgeVersionModel(Base):
    """Immutable edge historical version."""

    __tablename__ = "evidence_graph_edge_versions_t117"

    version_id = Column(String(64), primary_key=True)
    edge_id = Column(
        String(64),
        ForeignKey("evidence_graph_edges_t117.edge_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    relationship_type = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    edge = relationship("EvidenceGraphEdgeModel", back_populates="versions")


class EvidenceGraphSnapshotModel(Base):
    """Immutable point-in-time snapshot entity."""

    __tablename__ = "evidence_graph_snapshots_t117"

    snapshot_id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    graph_version = Column(Integer, default=1, nullable=False)
    node_count = Column(Integer, default=0, nullable=False)
    edge_count = Column(Integer, default=0, nullable=False)
    query_scope_json = Column(JSON, nullable=False, default=dict)
    filters_json = Column(JSON, nullable=False, default=dict)
    checksum = Column(String(64), nullable=False, default="", index=True)
    creation_reason = Column(String(256), nullable=False, default="AUDIT_SNAPSHOT")
    snapshot_data_json = Column(JSON, nullable=False, default=dict)


class DependencyImpactModel(Base):
    """Historical record of blast-radius and impact evaluations."""

    __tablename__ = "dependency_impacts_t117"

    impact_id = Column(String(64), primary_key=True)
    target_node_id = Column(String(64), nullable=False, index=True)
    target_node_type = Column(String(32), nullable=False)
    root_cause_node_id = Column(String(64), nullable=False, index=True)
    cause_reason = Column(String(256), nullable=False)
    severity = Column(String(32), nullable=False, default="DIRECT")
    impact_payload_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class RevalidationCandidateModel(Base):
    """Revalidation items for Attention/Control Plane."""

    __tablename__ = "revalidation_candidates_t117"

    candidate_id = Column(String(64), primary_key=True)
    affected_node_id = Column(String(64), nullable=False, index=True)
    affected_node_type = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    upstream_cause_id = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, default="DIRECT")
    freshness_state = Column(String(32), nullable=False, default="STALE")
    decision_impact = Column(String(256), nullable=True)
    mission_impact = Column(String(256), nullable=True)
    resource_estimate = Column(Float, nullable=False, default=1.0)
    expected_information_value = Column(Float, nullable=False, default=0.8)
    deadline = Column(DateTime(timezone=True), nullable=True)
    required_capability = Column(String(64), nullable=False, default="general_verification")
    recommended_next_step = Column(String(32), nullable=False, default="REVALIDATE_NOW")
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ProvenanceGapModel(Base):
    """Explicitly identified provenance gap."""

    __tablename__ = "provenance_gaps_t117"

    gap_id = Column(String(64), primary_key=True)
    affected_node_id = Column(String(64), nullable=False, index=True)
    missing_relationship = Column(String(64), nullable=False)
    expected_node_type = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False, default="POSSIBLE")
    recoverable = Column(Boolean, nullable=False, default=True)
    acquisition_method = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class EvidenceFragilityModel(Base):
    """Multi-dimensional fragility assessments."""

    __tablename__ = "evidence_fragility_t117"

    assessment_id = Column(String(64), primary_key=True)
    node_id = Column(String(64), nullable=False, index=True)
    source_concentration_score = Column(Float, nullable=False, default=0.0)
    provenance_completeness_score = Column(Float, nullable=False, default=1.0)
    freshness_score = Column(Float, nullable=False, default=1.0)
    reproducibility_score = Column(Float, nullable=False, default=1.0)
    dependency_depth = Column(Integer, nullable=False, default=1)
    contradiction_exposure_score = Column(Float, nullable=False, default=0.0)
    single_source_dependence = Column(Boolean, nullable=False, default=False)
    transformation_count = Column(Integer, nullable=False, default=0)
    unresolved_gaps_count = Column(Integer, nullable=False, default=0)
    overall_fragility_label = Column(String(32), nullable=False, default="LOW")
    dimension_findings_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class EvidenceGraphEventModel(Base):
    """Event ledger for graph operations."""

    __tablename__ = "evidence_graph_events_t117"

    event_id = Column(String(64), primary_key=True)
    event_type = Column(String(64), nullable=False, index=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    causation_id = Column(String(64), nullable=True)
    actor_component = Column(String(64), nullable=False, default="evidence_graph")
    object_id = Column(String(64), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    payload_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
