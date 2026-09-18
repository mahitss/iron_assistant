"""SQLAlchemy persistence models for Kairo Autonomous Attention & Cognitive Resource Allocation Engine (Task 70)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
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


# ============================================================================
# Task 109 Persistence Models
# ============================================================================

class AttentionCandidateT109Model(Base):
    """Task 109 First-Class Attention Candidate Persistence."""

    __tablename__ = "attention_candidates_t109"

    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target: Mapped[str] = mapped_column(String(128), default="unspecified", nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), index=True, default="CREATED", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Cross-subsystem links
    related_mission: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    related_situation: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    related_goal: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    related_decision: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    related_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_capability: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_user_intent: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Scores & Status
    salience_composite: Mapped[float] = mapped_column(Float, default=0.5, nullable=False, index=True)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    freshness: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    age_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    deferral_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aging_boost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_adversarial_dampened: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    score_details_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    evidence_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_attn_t109_tenant_type_score", "tenant_id", "type", "salience_composite"),
        Index("ix_attn_t109_tenant_lifecycle", "tenant_id", "lifecycle"),
    )


class AttentionEvidenceModel(Base):
    """Task 109 Auditable Evidence Backing Candidates."""

    __tablename__ = "attention_evidence"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_uri: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), default="INTERNAL_SIGNAL", nullable=False)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    credibility: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    claim: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw_payload_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class FocusSessionModel(Base):
    """Task 109 Active and Nested Focus Sessions."""

    __tablename__ = "focus_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    primary_target_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), default="USER_REQUEST", nullable=False)
    expected_duration_sec: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    resource_budget_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    interruption_policy: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    dependencies_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    success_condition: Mapped[str] = mapped_column(Text, default="Objective accomplished", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    resumption_context_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FocusTransitionModel(Base):
    """Task 109 Focus Switching Audit Records."""

    __tablename__ = "focus_transitions"

    transition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    previous_target: Mapped[str | None] = mapped_column(String(128), nullable=True)
    new_target: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    switching_cost: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class InterruptionDecisionModel(Base):
    """Task 109 Interruption Governance Decisions."""

    __tablename__ = "interruption_decisions"

    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    incoming_candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    should_interrupt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cost_breakdown_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AttentionBudgetModel(Base):
    """Task 109 Cognitive Budget Persistence."""

    __tablename__ = "attention_budgets"

    budget_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    active_reasoning_pct: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    background_pct: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    pending_queue_slots: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    reserved_emergency_pct: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    consumed_budget_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    context_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    context_token_capacity: Mapped[int] = mapped_column(Integer, default=128000, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AttentionAllocationModel(Base):
    """Task 109 Formal Resource Economy Demand Requests."""

    __tablename__ = "attention_allocations"

    allocation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    estimated_reasoning_cost: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    expected_benefit: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    urgency: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    resource_class: Mapped[str] = mapped_column(String(64), default="STANDARD_REASONING", nullable=False)
    economy_status: Mapped[str] = mapped_column(String(32), default="REQUESTED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AttentionSuppressionModel(Base):
    """Task 109 Deduplication & Storm Suppression Records."""

    __tablename__ = "attention_suppressions"

    suppression_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    suppressed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AttentionWatchModel(Base):
    """Task 109 Bounded Waiting Condition Watches."""

    __tablename__ = "attention_watches"

    watch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    condition_type: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_expr: Mapped[str] = mapped_column(Text, nullable=False)
    reconsideration_trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AttentionSnapshotT109Model(Base):
    """Task 109 Decision-Time Cognitive Attention Snapshot."""

    __tablename__ = "attention_snapshots_t109"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    health_status: Mapped[str] = mapped_column(String(64), default="HEALTHY", nullable=False)
    active_focus_session_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    nested_stack_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    queue_summary_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    budget_summary_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    active_missions_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    active_intents_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AttentionEventT109Model(Base):
    """Task 109 Audit Telemetry Event Stream."""

    __tablename__ = "attention_events_t109"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    candidate_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

