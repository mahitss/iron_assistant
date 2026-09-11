"""SQLAlchemy persistence models for Kairo Autonomous Attention & Cognitive Resource Allocation Engine (Task 70)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AttentionCandidateModel(Base):
    """Persists attention candidates with multi-dimensional scoring, lifecycle state, and references."""

    __tablename__ = "attention_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    attention_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Independent Dimensions
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    urgency: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    risk: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    novelty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    change_magnitude: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    goal_alignment: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    deadline_pressure: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dependency_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Composite & Lifecycle
    attention_score: Mapped[float] = mapped_column(Float, index=True, default=0.0, nullable=False)
    threshold: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    current_state: Mapped[str] = mapped_column(String(32), index=True, default="UNSEEN", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Subsystem Cross-References
    goal_refs_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    mission_refs_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    task_refs_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    incident_refs_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    decision_refs_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    # Requirements
    required_capabilities_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    required_agents_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    required_tools_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    provenance_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    # Preemption, Delegation & Aging
    context_snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delegated_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delegation_history_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    deferral_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aging_boost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interruption_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_attn_cand_tenant_state_score", "tenant_id", "current_state", "attention_score"),
        Index("ix_attn_cand_source", "tenant_id", "source_type", "source_id"),
    )


class AttentionSnapshotModel(Base):
    """Point-in-time snapshot of the cognitive attention engine state for replay and audit."""

    __tablename__ = "attention_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="NORMAL_MODE", nullable=False)
    current_focus_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stack_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    queue_summary_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    resource_budget_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    active_goal_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_attn_snap_tenant_created", "tenant_id", "created_at"),)


class AttentionAuditLogModel(Base):
    """Immutable audit trail for attention transitions, preemptions, and escalations."""

    __tablename__ = "attention_audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    log_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    attention_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    score_breakdown_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_attn_audit_tenant_attn_action", "tenant_id", "attention_id", "action"),)
