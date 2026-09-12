"""SQLAlchemy ORM models for Kairo Autonomous Resource Economy,
Capability Allocation & Cognitive Budget Engine (Task 77).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CognitiveBudgetModel(Base):
    """Hierarchical multi-scope cognitive budgets."""

    __tablename__ = "cognitive_budgets"

    budget_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="default_tenant", index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="GLOBAL", index=True, nullable=False)
    scope_id: Mapped[str] = mapped_column(String(128), default="global", index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="CREATED", index=True, nullable=False)
    limits: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    consumed: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    reserved: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    near_limit_threshold: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    reset_frequency: Mapped[str] = mapped_column(String(32), default="NEVER", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)


class ResourceDemandModel(Base):
    """Calibrated resource demand predictions for scheduled and executing tasks."""

    __tablename__ = "resource_demands"

    demand_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    capability_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    model_calls: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expected_time_s: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    lower_bound: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    upper_bound: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    uncertainty_pct: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_preemptible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class TaskPreemptionModel(Base):
    """Audit log of task preemption checkpoints and resume state."""

    __tablename__ = "task_preemptions"

    preemption_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    preempted_by_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="RUNNING", index=True, nullable=False)
    checkpoint_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    saved_context_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wait_time_s: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_of_preemption: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResourceContentionRecordModel(Base):
    """Historical records of resource contention events and deadlock cycle resolutions."""

    __tablename__ = "resource_contention_records"

    contention_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    competing_tasks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), default="SEQUENCE", nullable=False)
    total_demanded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    available_capacity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cycle_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wait_graph: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ResourceEfficiencyLogModel(Base):
    """Execution telemetry tracking resource consumption efficiency and degraded modes."""

    __tablename__ = "resource_efficiency_logs"

    log_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    capability_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    model_used: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    degradation_tier: Mapped[str] = mapped_column(String(32), default="FULL_FIDELITY", nullable=False)
    trade_off_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
