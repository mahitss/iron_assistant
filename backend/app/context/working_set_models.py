"""SQLAlchemy models for Task 110:
Autonomous Cognitive Working Set, Context Assembly, Relevance Packing & Context Lifecycle Engine.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkingSetModel(Base):
    """Authoritative cognitive working set bound to a specific cognitive operation."""

    __tablename__ = "working_sets_t110"

    working_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="default", index=True, nullable=False)
    user_scope: Mapped[str] = mapped_column(String(64), server_default="default_user", index=True, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    operation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    mission_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    goal_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    situation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    action_transaction_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String(32), server_default="DRAFT", index=True, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    completeness_estimate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence_summary: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compressed_item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_untrusted_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sections_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    budget_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    conflicts_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    gaps_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    exclusions_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    pinned_items_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_ws_t110_tenant_user_op", "tenant_id", "user_scope", "operation_type"),
        Index("ix_ws_t110_lifecycle_created", "lifecycle", "created_at"),
    )


class WorkingSetVersionModel(Base):
    """Historical version delta tracking for working sets across iterative revalidations."""

    __tablename__ = "working_set_versions_t110"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    modified_sections_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    added_item_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    removed_item_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_wsv_t110_ws_ver", "working_set_id", "version", unique=True),)


class ContextItemModel(Base):
    """Persisted context items with inclusion semantics, scores, and provenance."""

    __tablename__ = "context_items_t110"

    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    section: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    inclusion: Mapped[str] = mapped_column(String(32), default="OPTIONAL", nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    relevance_components_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    freshness_classification: Mapped[str] = mapped_column(String(32), default="FRESH", nullable=False)
    freshness_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    provenance_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    compression_level: Mapped[str] = mapped_column(String(32), default="NONE", nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_untrusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dependencies_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_citem_t110_ws_section", "working_set_id", "section"),
        Index("ix_citem_t110_ws_score", "working_set_id", "relevance_score"),
    )


class ContextSectionModel(Base):
    """Logical section definitions and metrics within working sets."""

    __tablename__ = "context_sections_t110"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    section_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_empty: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_csec_t110_ws_type", "working_set_id", "section_type", unique=True),)


class ContextBudgetModel(Base):
    """Resource token and latency allocations bound to working sets."""

    __tablename__ = "context_budgets_t110"

    budget_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=8000, nullable=False)
    max_bytes: Mapped[int] = mapped_column(Integer, default=64000, nullable=False)
    max_items: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    max_retrieval_calls: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    latency_budget_ms: Mapped[float] = mapped_column(Float, default=250.0, nullable=False)
    used_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retrieval_calls_made: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_exhausted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exhaustion_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextTransformationModel(Base):
    """Audit log of transformations and compressions applied to context items."""

    __tablename__ = "context_transformations_t110"

    transformation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    transformation_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    input_item_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    output_item_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    information_loss: Mapped[str] = mapped_column(String(32), default="NONE", nullable=False)
    is_reversible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transformed_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextDependencyModel(Base):
    """Directional dependency links between context items."""

    __tablename__ = "context_dependencies_t110"

    dependency_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_item_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_item_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    relationship: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextConflictModel(Base):
    """Preserved context conflicts surfaced to reasoning operations."""

    __tablename__ = "context_conflicts_t110"

    conflict_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    competing_item_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    conflict_dimension: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), default="UNRESOLVED", nullable=False)
    arbitration_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextGapModel(Base):
    """Explicit missing context elements required for high-confidence reasoning."""

    __tablename__ = "context_gaps_t110"

    gap_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    missing_information: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    expected_source: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_impact: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    suggested_retrieval: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_retrieval_cost: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextLeaseModel(Base):
    """Short-lived validity leases issued for assembled working sets."""

    __tablename__ = "context_leases_t110"

    lease_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    working_set_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="VALID", index=True, nullable=False)
    ttl_seconds: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ContextQualityModel(Base):
    """Multi-dimensional quality scorecards for assembled working sets."""

    __tablename__ = "context_quality_assessments_t110"

    assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    provenance_coverage_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    contradiction_visibility_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    redundancy_penalty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    compression_quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    budget_efficiency_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    latency_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_diversity_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    task_alignment_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    safety_coverage_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    isolation_correctness_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    composite_quality: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextSnapshotModelT110(Base):
    """Immutable audit records answering what exact context Kairo possessed when deciding."""

    __tablename__ = "context_snapshots_t110"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    working_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    operation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    item_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    source_versions_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    transformations_applied_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    freshness_summary_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gap_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    has_untrusted_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextFeedbackModelT110(Base):
    """Post-deliberation feedback capturing how the working set was utilized downstream."""

    __tablename__ = "context_feedback_t110"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    working_set_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    operation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    items_used_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    items_ignored_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    items_misleading_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    items_missing_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    was_compression_harmful: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    was_freshness_sufficient: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    context_size_rating: Mapped[str] = mapped_column(String(32), default="OPTIMAL", nullable=False)
    downstream_outcome: Mapped[str] = mapped_column(String(32), default="SUCCESS", nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
