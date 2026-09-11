"""SQLAlchemy database models for Autonomous World Model & Long-Horizon Foresight Engine (Task 65)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ForesightEntityModel(Base):
    """Persistent entity record in the Autonomous World Model."""

    __tablename__ = "foresight_entities"

    entity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="UNKNOWN", nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), default="SYSTEM", nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    uncertainty: Mapped[str] = mapped_column(String(32), default="LIKELY", nullable=False)
    authority: Mapped[str] = mapped_column(String(32), default="OBSERVED", nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    __table_args__ = (
        Index("ix_foresight_ent_tenant_type", "tenant_id", "type"),
        Index("ix_foresight_ent_state", "state"),
    )


class ForesightRelationshipModel(Base):
    """Persistent relationship and causal edge connecting entities."""

    __tablename__ = "foresight_relationships"

    rel_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    causal_strength: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    conditions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="SYSTEM", nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_foresight_rel_src_tgt", "source_entity_id", "target_entity_id"),
        Index("ix_foresight_rel_type", "relationship_type"),
    )


class ForesightStateHistoryModel(Base):
    """Immutable point-in-time state version records for historical reconstruction."""

    __tablename__ = "foresight_state_history"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    authority: Mapped[str] = mapped_column(String(32), default="OBSERVED", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (Index("ix_foresight_hist_entity_obs", "entity_id", "observed_at"),)


class ForesightForecastModel(Base):
    """Persistent long-horizon range forecasts."""

    __tablename__ = "foresight_forecasts"

    forecast_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic: Mapped[str] = mapped_column(String(256), nullable=False)
    horizon: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    intervals_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prediction_summary: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    competing_hypotheses_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), default="ensemble", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    actual_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    calibration_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ForesightScenarioModel(Base):
    """Persistent scenario sandbox branches."""

    __tablename__ = "foresight_scenarios"

    scenario_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="BASELINE", nullable=False, index=True)
    horizon: Mapped[str] = mapped_column(String(32), nullable=False)
    initial_state_summary: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    interventions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    expected_changes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risks_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    opportunities_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_robust: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sensitivity_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ForesightRiskModel(Base):
    """Persistent entries in the Strategic Risk Register."""

    __tablename__ = "foresight_risks"

    risk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    impact: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    time_horizon: Mapped[str] = mapped_column(String(32), default="MID_FUTURE_1M", nullable=False)
    dependencies_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    mitigations_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ForesightOpportunityModel(Base):
    """Persistent entries in the Strategic Opportunity Register."""

    __tablename__ = "foresight_opportunities"

    opportunity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    potential_value: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    time_horizon: Mapped[str] = mapped_column(String(32), default="MID_FUTURE_1M", nullable=False)
    dependencies_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risks_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    optionality_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="IDENTIFIED", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ForesightEarlyWarningModel(Base):
    """Persistent leading indicators and emerging risk warnings."""

    __tablename__ = "foresight_early_warnings"

    signal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False, index=True)
    trend: Mapped[str] = mapped_column(String(32), default="ACCELERATING", nullable=False)
    affected_entities_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    trigger_condition: Mapped[str] = mapped_column(String(256), nullable=False)
    leading_indicators_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    blast_radius_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ForesightMonitoringPlanModel(Base):
    """Persistent bounded monitoring plans."""

    __tablename__ = "foresight_monitoring_plans"

    plan_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(32), default="risk", nullable=False)
    signals_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    thresholds_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    frequency_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class ForesightAuditRecordModel(Base):
    """Cryptographic hash chain audit trail records."""

    __tablename__ = "foresight_audit_records"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
