"""SQLAlchemy models for Kairo Autonomous Resilience, Recovery,
Containment, and Adaptive Defense Engine (Task 76).
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ResilienceAssessmentModel(Base):
    """Stores full systemic resilience evaluations and dimension scorecards."""

    __tablename__ = "resilience_assessments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default_tenant", nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", nullable=False)
    target: Mapped[str] = mapped_column(String(128), default="CORE", nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="ASSESSED", nullable=False, index=True)
    scorecard: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    identified_weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    gaps = relationship("ResilienceGapModel", back_populates="assessment", cascade="all, delete-orphan")


class ResilienceGapModel(Base):
    """Stores identified resilience gaps, vulnerabilities, and missing controls."""

    __tablename__ = "resilience_gaps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assessment_id: Mapped[str] = mapped_column(String(64), ForeignKey("resilience_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default_tenant", nullable=False, index=True)
    gap_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    affected_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    remediation_candidate: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    assessment = relationship("ResilienceAssessmentModel", back_populates="gaps")


class RecoveryPlanModel(Base):
    """Stores multi-strategy recovery plans, containment points, and verification criteria."""

    __tablename__ = "resilience_recovery_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assessment_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("resilience_assessments.id", ondelete="SET NULL"), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default_tenant", nullable=False, index=True)
    incident_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cascade_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(32), default="DETECTED", nullable=False, index=True)
    selected_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    containment_points: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    recovery_paths: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    execution_order: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preconditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    verification_criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    residual_risk: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    return_to_normal_plan: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    steps = relationship("RecoveryExecutionStepModel", back_populates="plan", cascade="all, delete-orphan")


class RecoveryExecutionStepModel(Base):
    """Audit record for individual recovery & containment step executions."""

    __tablename__ = "resilience_recovery_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), ForeignKey("resilience_recovery_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default_tenant", nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    action_id: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_performed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    plan = relationship("RecoveryPlanModel", back_populates="steps")


class PostIncidentLessonModel(Base):
    """Structured knowledge extracted from incidents and recovery outcomes."""

    __tablename__ = "resilience_lessons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default_tenant", nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recovery_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    what_was_expected: Mapped[str] = mapped_column(Text, nullable=False)
    what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_mattered: Mapped[str] = mapped_column(Text, nullable=False)
    what_should_change: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OBSERVED", nullable=False, index=True)
    learned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AdaptiveDefenseRecommendationModel(Base):
    """Autonomous suggestions to strengthen defense and reduce systemic fragility."""

    __tablename__ = "resilience_adaptive_recommendations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default_tenant", nullable=False, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_entity: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    cost: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    reversibility: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    risk_reduction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


Index("ix_resilience_gaps_tenant_target", ResilienceGapModel.tenant_id, ResilienceGapModel.target_entity)
Index("ix_recovery_plans_tenant_state", RecoveryPlanModel.tenant_id, RecoveryPlanModel.state)
Index("ix_recovery_steps_plan_state", RecoveryExecutionStepModel.plan_id, RecoveryExecutionStepModel.state)
