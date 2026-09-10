"""SQLAlchemy ORM models for Strategic Planning & Long-Horizon Execution Engine (Task 58)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class StrategicPlanModel(Base):
    __tablename__ = "strategic_plans"

    id = Column(String(64), primary_key=True, default=lambda: f"spl_{uuid.uuid4().hex[:12]}")
    plan_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    purpose = Column(Text, nullable=False)
    goal_id = Column(String(128), nullable=True, index=True)
    decision_id = Column(String(128), nullable=True, index=True)
    current_state_summary = Column(Text, nullable=False)
    desired_state_summary = Column(Text, nullable=False)
    strategy_type = Column(String(64), nullable=False, default="INCREMENTAL")
    status = Column(String(32), nullable=False, default="DRAFT", index=True)
    confidence = Column(Float, nullable=False, default=0.85)
    owner = Column(String(128), nullable=False, default="OWNER_UNASSIGNED")
    deadline = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    provenance = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_strategic_plans_status_goal", "status", "goal_id"),
        Index("ix_strategic_plans_created", "created_at"),
    )


class PlanPhaseModel(Base):
    __tablename__ = "plan_phases"

    id = Column(String(64), primary_key=True, default=lambda: f"pph_{uuid.uuid4().hex[:12]}")
    phase_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("strategic_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phase_order = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="PLANNED", index=True)
    entry_criteria = Column(JSON, nullable=False, default=list)
    exit_criteria = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)


class PlanMilestoneModel(Base):
    __tablename__ = "plan_milestones"

    id = Column(String(64), primary_key=True, default=lambda: f"pml_{uuid.uuid4().hex[:12]}")
    milestone_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("strategic_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    phase_id = Column(String(64), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    weight = Column(Float, nullable=False, default=1.0)
    target_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    dependencies = Column(JSON, nullable=False, default=list)
    verification_criteria = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)


class PlanWorkPackageModel(Base):
    __tablename__ = "plan_work_packages"

    id = Column(String(64), primary_key=True, default=lambda: f"pwp_{uuid.uuid4().hex[:12]}")
    package_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("strategic_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    phase_id = Column(String(64), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    owner = Column(String(128), nullable=False, default="OWNER_UNASSIGNED")
    status = Column(String(32), nullable=False, default="PLANNED", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)


class PlanTaskModel(Base):
    __tablename__ = "plan_tasks"

    id = Column(String(64), primary_key=True, default=lambda: f"ptk_{uuid.uuid4().hex[:12]}")
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("strategic_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    phase_id = Column(String(64), nullable=True, index=True)
    package_id = Column(String(64), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    owner = Column(String(128), nullable=False, default="OWNER_UNASSIGNED")
    status = Column(String(32), nullable=False, default="DRAFT", index=True)
    dependencies = Column(JSON, nullable=False, default=list)
    resources_required = Column(JSON, nullable=False, default=dict)
    duration_min = Column(Float, nullable=False, default=1.0)
    duration_expected = Column(Float, nullable=False, default=2.0)
    duration_max = Column(Float, nullable=False, default=4.0)
    is_irreversible = Column(Boolean, nullable=False, default=False)
    risk_level = Column(String(32), nullable=False, default="LOW")
    execution_wave = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)


class PlanCheckpointModel(Base):
    __tablename__ = "plan_checkpoints"

    id = Column(String(64), primary_key=True, default=lambda: f"pck_{uuid.uuid4().hex[:12]}")
    checkpoint_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("strategic_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_milestone_id = Column(String(64), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    expected_state = Column(JSON, nullable=False, default=dict)
    observed_state = Column(JSON, nullable=False, default=dict)
    variance_score = Column(Float, nullable=False, default=0.0)
    decision_action = Column(String(32), nullable=False, default="CONTINUE")
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)


class PlanRevisionModel(Base):
    __tablename__ = "plan_revisions"

    id = Column(String(64), primary_key=True, default=lambda: f"prev_{uuid.uuid4().hex[:12]}")
    revision_id = Column(String(64), unique=True, nullable=False, index=True)
    parent_plan_id = Column(String(64), ForeignKey("strategic_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False, default=1)
    reason = Column(Text, nullable=False)
    actor = Column(String(128), nullable=False)
    diff_summary = Column(JSON, nullable=False, default=dict)
    snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)


class PlanOutcomeModel(Base):
    __tablename__ = "plan_outcomes"

    id = Column(String(64), primary_key=True, default=lambda: f"pout_{uuid.uuid4().hex[:12]}")
    outcome_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("strategic_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    success = Column(Boolean, nullable=False, default=True)
    actual_duration = Column(Float, nullable=False, default=0.0)
    actual_cost = Column(Float, nullable=False, default=0.0)
    estimation_error = Column(Float, nullable=False, default=0.0)
    lessons_learned = Column(JSON, nullable=False, default=list)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
