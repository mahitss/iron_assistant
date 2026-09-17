"""SQLAlchemy database models for Kairo Autonomous Goal Management & Mission Control (Task 66 & Task 100)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class GoalModel(Base):
    """Persistent goal entity in relational storage."""

    __tablename__ = "mission_goals"

    goal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(String(64), default="USER", nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(128), default="user", nullable=False)
    stakeholders_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    urgency: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    constraints_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success_criteria_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    failure_conditions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dependencies_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    resources_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risk_level: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    authority_scope: Mapped[str] = mapped_column(String(64), default="EXECUTE_LOW_RISK", nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="DRAFT", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    __table_args__ = (
        Index("ix_mission_goals_tenant_status", "tenant_id", "status"),
    )


class MissionModel(Base):
    """Persistent mission execution record (Task 66 & Task 100)."""

    __tablename__ = "mission_records"

    mission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", nullable=False)
    goal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    authority_scope: Mapped[str] = mapped_column(String(64), default="EXECUTE_LOW_RISK", nullable=False)
    autonomy_level: Mapped[str] = mapped_column(String(32), default="BOUNDED_AUTONOMY", nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="DRAFT", nullable=False, index=True)
    health: Mapped[str] = mapped_column(String(64), default="ON_TRACK", nullable=False, index=True)
    health_dimensions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    strategic_importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    active_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_versions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    progress_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    active_situations_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active_decisions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active_actions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active_workflows_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active_agents_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    budget_limits_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    budget_consumed_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_context_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkpoints_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    blockers_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    __table_args__ = (
        Index("ix_mission_records_tenant_status", "tenant_id", "status"),
    )


class MissionObjectiveModel(Base):
    """Persistent hierarchical objective tier (Task 100)."""

    __tablename__ = "mission_objectives"

    objective_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_objective_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    ordering: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_criteria_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )


class MissionMilestoneModel(Base):
    """Persistent evidence-backed milestone records (Task 100)."""

    __tablename__ = "mission_milestones"

    milestone_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    objective_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    ordering: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dependencies_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    goal_linkage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success_criteria_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    verification_criteria_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_situation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )


class MissionAssumptionModel(Base):
    """Persistent explicit mission assumption records (Task 100)."""

    __tablename__ = "mission_assumptions"

    assumption_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="VALID", nullable=False, index=True)
    dependent_milestones_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dependent_plan_versions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class MissionDependencyModel(Base):
    """Persistent mission dependency records (Task 100)."""

    __tablename__ = "mission_dependencies"

    dependency_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(32), default="INTERNAL", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="AVAILABLE", nullable=False, index=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )


class MissionPlanVersionModel(Base):
    """Persistent immutable plan version history (Task 100)."""

    __tablename__ = "mission_plan_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    triggering_situation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    changed_assumptions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    changed_milestones_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    superseded_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decisions_linked_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    plan_spec_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MissionReviewModel(Base):
    """Persistent structured mission review records (Task 100)."""

    __tablename__ = "mission_reviews"

    review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    review_type: Mapped[str] = mapped_column(String(32), default="SCHEDULED", nullable=False, index=True)
    health_dimensions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    findings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    recommendations_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    actions_taken_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MissionCheckpointModel(Base):
    """Persistent checkpoints recorded along mission trajectory."""

    __tablename__ = "mission_checkpoints"

    checkpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risks_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    next_steps_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    verification_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False, index=True
    )


class MissionBlockerModel(Base):
    """Persistent blocker records."""

    __tablename__ = "mission_blockers"

    blocker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    blocker_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DETECTED", nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MissionPostmortemModel(Base):
    """Persistent postmortem retrospectives."""

    __tablename__ = "mission_postmortems"

    postmortem_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    final_status: Mapped[str] = mapped_column(String(64), nullable=False)
    what_worked_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    what_failed_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    unexpected_events_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    planning_errors_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    resource_problems_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    agent_performance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    lessons_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MissionAuditRecordModel(Base):
    """Append-only cryptographic SHA-256 audit chain storage."""

    __tablename__ = "mission_audit_records"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    authority: Mapped[str] = mapped_column(String(64), default="EXECUTE_LOW_RISK", nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
