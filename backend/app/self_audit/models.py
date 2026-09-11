"""SQLAlchemy database models for Kairo Metacognitive Control & Autonomous Self-Audit Engine (Task 67)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SelfModelEntity(Base):
    """Persistent representation of Kairo's operational self-model (Spec 3)."""

    __tablename__ = "self_models"

    self_model_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    limitations_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active_goals_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active_missions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    known_dependencies_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    current_state: Mapped[str] = mapped_column(String(64), default="CONFIDENT", nullable=False, index=True)
    uncertainties_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    known_failure_modes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    performance_metrics_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    calibration: Mapped[str] = mapped_column(String(64), default="WELL_CALIBRATED", nullable=False)
    resource_state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tool_state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    model_state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class BeliefModel(Base):
    """Persistent beliefs and revision lineage (Spec 7, 8)."""

    __tablename__ = "self_audit_beliefs"

    belief_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="ACTIVE", nullable=False, index=True)
    revisions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (Index("ix_self_audit_beliefs_tenant_status", "tenant_id", "status"),)


class SelfAuditRecordModel(Base):
    """Immutable audit run records (Spec 45, 66)."""

    __tablename__ = "self_audit_records"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    subject: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    audit_type: Mapped[str] = mapped_column(String(64), default="PERIODIC", nullable=False, index=True)
    depth: Mapped[str] = mapped_column(String(64), default="STANDARD", nullable=False)
    checks_performed_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="INFO", nullable=False, index=True)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    recommendations_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    verification_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (Index("ix_self_audit_records_tenant_type", "tenant_id", "audit_type"),)


class AuditFindingModel(Base):
    """Structured findings discovered during self-audits (Spec 50)."""

    __tablename__ = "self_audit_findings"

    finding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audit_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BehaviorBaselineModel(Base):
    """Behavioral baseline metrics for drift detection (Spec 33, 34)."""

    __tablename__ = "self_audit_baselines"

    baseline_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    normal_mean: Mapped[float] = mapped_column(Float, nullable=False)
    normal_std: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    drift_threshold_pct: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_drifting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    drift_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ErrorClusterModel(Base):
    """Recurring operational failure patterns (Spec 29, 31)."""

    __tablename__ = "self_audit_error_clusters"

    cluster_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    error_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pattern_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    recurring_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    root_cause_hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sample_error_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
