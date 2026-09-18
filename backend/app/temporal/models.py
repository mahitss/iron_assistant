"""SQLAlchemy models for Task 111:
KAIRO Autonomous Temporal Intelligence, Event History, Change Reconstruction,
Temporal Queries & "What Changed?" Engine.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class TemporalEventModel(Base):
    """Normalized temporal projection of an emitted event with multi-clock timestamps."""

    __tablename__ = "temporal_events_t111"

    temporal_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_event_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_version: Mapped[str] = mapped_column(String(16), default="v1", nullable=False)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    
    # Multi-clock timestamps
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    observed_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sequence_number: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    monotonic_timestamp: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_subsystem: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source_entity_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    parent_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    payload_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload_diff_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_untrusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_out_of_order: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    correction_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_tevt_category_event_time", "category", "event_time"),
        Index("ix_tevt_entity_event_time", "source_entity_id", "event_time"),
        Index("ix_tevt_correlation_event_time", "correlation_id", "event_time"),
    )


class TemporalEntityModel(Base):
    """Entity whose state evolution is tracked across time."""

    __tablename__ = "temporal_entities_t111"

    entity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(64), server_default="DEFAULT", index=True, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_state: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_transition_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    state_attributes_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    provenance_source: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    __table_args__ = (
        Index("ix_tent_type_scope", "entity_type", "scope"),
    )


class TemporalStateTransitionModel(Base):
    """Explicit state transitions between consecutive states."""

    __tablename__ = "temporal_state_transitions_t111"

    transition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    previous_state: Mapped[str] = mapped_column(String(64), nullable=False)
    next_state: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_event_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    expectation_status: Mapped[str] = mapped_column(String(32), default="OBSERVED", nullable=False)
    evidence_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    attribution: Mapped[str] = mapped_column(String(32), default="UNATTRIBUTED", nullable=False)
    attributed_cause: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    scope: Mapped[str] = mapped_column(String(64), server_default="DEFAULT", nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_ttrans_entity_ts", "entity_id", "timestamp"),
        Index("ix_ttrans_attribution_ts", "attribution", "timestamp"),
    )


class TemporalChangeSetModel(Base):
    """Persisted diff changesets between snapshots or checkpoints."""

    __tablename__ = "temporal_changesets_t111"

    changeset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    to_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    from_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    to_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    added_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    removed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    modified_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    degraded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unattributed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class TemporalChangeRecordModel(Base):
    """Individual atomic change record."""

    __tablename__ = "temporal_change_records_t111"

    change_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    changeset_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    attribute_path: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    attribution: Mapped[str] = mapped_column(String(32), default="UNATTRIBUTED", nullable=False)
    attributed_action_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attributed_actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    causal_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    impact_level: Mapped[str] = mapped_column(String(16), default="LOW", nullable=False)

    __table_args__ = (
        Index("ix_tchg_entity_ts", "entity_id", "timestamp"),
    )


class TemporalAnomalyModel(Base):
    """Detected timing or temporal integrity violation."""

    __tablename__ = "temporal_anomalies_t111"

    anomaly_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    anomaly_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    event_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="WARNING", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    remediation_suggested: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_adversarial_suspect: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TemporalGapModel(Base):
    """Detected period of unobserved telemetry or missing observations."""

    __tablename__ = "temporal_gaps_t111"

    gap_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subsystem: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    gap_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gap_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    is_offline_period: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_impact: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)


class TemporalWatermarkModel(Base):
    """Source, ingestion, processing, and reconciliation watermarks."""

    __tablename__ = "temporal_watermarks_t111"

    watermark_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subsystem: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    source_watermark: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ingestion_watermark: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processing_watermark: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    reconciliation_watermark: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class TemporalCheckpointModel(Base):
    """Named stable point in time for fast diffing and rollback reconstruction."""

    __tablename__ = "temporal_checkpoints_t111"

    checkpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    checkpoint_type: Mapped[str] = mapped_column(String(32), default="MANUAL", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    active_entity_states_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    state_snapshot_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    creator: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
