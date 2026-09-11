"""SQLAlchemy 2 models for Kairo Autonomous Risk Propagation & Cascade Engine (Task 75)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

from app.db.session import Base


class PropagationAnalysisModel(Base):
    """Ledger of systemic propagation analyses (Spec 4)."""
    __tablename__ = "propagation_analyses"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True, default="default_tenant")
    scope = Column(String(32), nullable=False, default="SERVICE")
    trigger = Column(String(256), nullable=False)
    trigger_type = Column(String(32), nullable=False, default="STATE_CHANGE")
    origin_entity = Column(String(256), nullable=False, index=True)
    origin_state = Column(JSON, nullable=False, default=dict)
    origin_event = Column(JSON, nullable=True)
    origin_forecast = Column(JSON, nullable=True)
    graph_snapshot_id = Column(String(64), nullable=False, default="")
    causal_model_reference = Column(String(128), nullable=True)
    world_state_reference = Column(String(128), nullable=True)
    analysis_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    horizon = Column(String(32), nullable=False, default="MEDIUM")
    propagation_depth = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False, default=0.8)
    uncertainty = Column(JSON, nullable=False, default=dict)
    assumptions = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, index=True, default="DISCOVERED")
    direct_effects = Column(JSON, nullable=False, default=list)
    second_order_effects = Column(JSON, nullable=False, default=list)
    resilience_assessment = Column(JSON, nullable=False, default=dict)
    containment_options = Column(JSON, nullable=False, default=list)
    mitigation_candidates = Column(JSON, nullable=False, default=list)
    fingerprint = Column(String(64), nullable=False, index=True, default="")
    provenance = Column(JSON, nullable=False, default=dict)
    is_truncated = Column(Boolean, nullable=False, default=False)
    truncation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class PropagationCascadeModel(Base):
    """Detected systemic cascade chains (Spec 11, 12)."""
    __tablename__ = "propagation_cascades"

    id = Column(String(64), primary_key=True)
    propagation_id = Column(String(64), nullable=False, index=True)
    cascade_type = Column(String(32), nullable=False, default="DEPENDENCY_CASCADE")
    nodes = Column(JSON, nullable=False, default=list)
    edges = Column(JSON, nullable=False, default=list)
    total_depth = Column(Integer, nullable=False, default=0)
    cumulative_delay_seconds = Column(Float, nullable=False, default=0.0)
    amplification_detected = Column(Boolean, nullable=False, default=False)
    feedback_type = Column(String(32), nullable=False, default="STABILIZING_FEEDBACK")
    likelihood = Column(Float, nullable=False, default=0.5)
    impact = Column(JSON, nullable=False, default=dict)
    fingerprint = Column(String(64), nullable=False, index=True, default="")
    status = Column(String(32), nullable=False, default="DISCOVERED")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class PropagationBottleneckModel(Base):
    """Critical bottlenecks and SPoFs identified in system structure (Spec 13, 14)."""
    __tablename__ = "propagation_bottlenecks"

    id = Column(String(64), primary_key=True)
    propagation_id = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(256), nullable=False, index=True)
    name = Column(String(256), nullable=False, default="")
    downstream_reach = Column(Integer, nullable=False, default=0)
    dependency_count = Column(Integer, nullable=False, default=0)
    centrality_score = Column(Float, nullable=False, default=0.0)
    critical_path_participant = Column(Boolean, nullable=False, default=False)
    resource_contention_index = Column(Float, nullable=False, default=0.0)
    failure_propagation_potential = Column(Float, nullable=False, default=0.0)
    spof_criticality = Column(String(32), nullable=False, default="LOW")
    redundancy_state = Column(String(32), nullable=False, default="REDUNDANCY_UNKNOWN")
    substitutes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class PropagationEvaluationModel(Base):
    """Post-outcome verification tracking predicted vs realized cascades (Spec 59, 60)."""
    __tablename__ = "propagation_evaluations"

    id = Column(String(64), primary_key=True)
    propagation_id = Column(String(64), nullable=False, index=True)
    target_origin = Column(String(256), nullable=False)
    predicted_nodes = Column(JSON, nullable=False, default=list)
    actual_nodes = Column(JSON, nullable=False, default=list)
    missed_nodes = Column(JSON, nullable=False, default=list)
    false_nodes = Column(JSON, nullable=False, default=list)
    node_precision = Column(Float, nullable=False, default=1.0)
    node_recall = Column(Float, nullable=False, default=1.0)
    path_precision = Column(Float, nullable=False, default=1.0)
    path_recall = Column(Float, nullable=False, default=1.0)
    depth_error = Column(Integer, nullable=False, default=0)
    timing_error_seconds = Column(Float, nullable=False, default=0.0)
    impact_estimation_error = Column(Float, nullable=False, default=0.0)
    warning_lead_time_seconds = Column(Float, nullable=False, default=0.0)
    false_positive = Column(Boolean, nullable=False, default=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class PropagationSnapshotModel(Base):
    """Versioned graph and topology snapshots for zero-leakage backtesting (Spec 6, 62)."""
    __tablename__ = "propagation_snapshots"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True, default="default_tenant")
    graph_version = Column(Integer, nullable=False, default=1)
    snapshot_timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    node_count = Column(Integer, nullable=False, default=0)
    edge_count = Column(Integer, nullable=False, default=0)
    entities = Column(JSON, nullable=False, default=list)
    relationships = Column(JSON, nullable=False, default=list)
    source_references = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
