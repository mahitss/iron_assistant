"""SQLAlchemy ORM models for Continuous Self-Optimization & Adaptive Control Engine (Task 62)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

JSON_TYPE = JSONB().with_variant(Text, "sqlite")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class OptimizationObjectiveModel(Base):
    __tablename__ = "optimization_objectives"

    objective_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(32), default="MINIMIZE")
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class OptimizationMetricModel(Base):
    __tablename__ = "optimization_metrics"

    measurement_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(128), default="telemetry")
    scope: Mapped[str] = mapped_column(String(128), default="global")
    tags: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, index=True)


class OptimizationBaselineModel(Base):
    __tablename__ = "optimization_baselines"

    baseline_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    environment: Mapped[str] = mapped_column(String(64), default="production")
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class OptimizationExperimentModel(Base):
    __tablename__ = "optimization_experiments"

    experiment_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    target_metrics: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    control_parameters: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    variants: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, default=list)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    safety_gates: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    stop_conditions: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class OptimizationChangeSetModel(Base):
    __tablename__ = "optimization_change_sets"

    change_set_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    target_parameter: Mapped[str] = mapped_column(String(128), nullable=False)
    before_state: Mapped[float] = mapped_column(Float, nullable=False)
    after_state: Mapped[float] = mapped_column(Float, nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(String(32), default="LOW")
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approver: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rollback_strategy: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class OptimizationCanaryModel(Base):
    __tablename__ = "optimization_canaries"

    canary_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    change_set_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rollout_state: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    traffic_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    blast_radius_scope: Mapped[str] = mapped_column(String(64), default="canary_partition")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_threshold_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class OptimizationDriftModel(Base):
    __tablename__ = "optimization_drift_records"

    drift_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    drift_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM")
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    divergence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class OptimizationAuditModel(Base):
    __tablename__ = "optimization_audit_log"

    entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    recommendation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_set_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
