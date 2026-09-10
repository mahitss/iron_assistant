"""SQLAlchemy ORM models for Kairo Simulation, Digital World Model & Counterfactual Planning (Task 56)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SimulationSnapshotModel(Base):
    __tablename__ = "simulation_snapshots"

    id = Column(String(64), primary_key=True, default=lambda: f"ssnap_{uuid.uuid4().hex[:12]}")
    snapshot_id = Column(String(64), unique=True, nullable=False, index=True)
    source_entity = Column(String(128), nullable=False, default="digital_twin")
    world_state = Column(JSON, nullable=False, default=dict)
    digital_twin_state = Column(JSON, nullable=False, default=dict)
    telemetry_state = Column(JSON, nullable=False, default=dict)
    captured_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    baseline_hash = Column(String(64), nullable=False, index=True)
    is_stale = Column(Boolean, nullable=False, default=False)
    staleness_reason = Column(String(256), nullable=True)
    provenance = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_ssnap_source_ts", "source_entity", "captured_at"),
    )


class ScenarioModel(Base):
    __tablename__ = "simulation_scenarios"

    id = Column(String(64), primary_key=True, default=lambda: f"scen_{uuid.uuid4().hex[:12]}")
    scenario_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    scenario_type = Column(String(64), nullable=False, default="CUSTOM")
    baseline_snapshot_id = Column(String(64), nullable=False, index=True)
    interventions = Column(JSON, nullable=False, default=list)
    assumptions = Column(JSON, nullable=False, default=list)
    constraints = Column(JSON, nullable=False, default=list)
    objectives = Column(JSON, nullable=False, default=list)
    horizon = Column(String(64), nullable=False, default="SHORT_TERM")
    status = Column(String(64), nullable=False, default="CREATED")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_scen_type_status", "scenario_type", "status"),
    )


class SimulationModel(Base):
    __tablename__ = "simulations"

    id = Column(String(64), primary_key=True, default=lambda: f"sim_{uuid.uuid4().hex[:12]}")
    simulation_id = Column(String(64), unique=True, nullable=False, index=True)
    source_snapshot_id = Column(String(64), nullable=False, index=True)
    scenario_id = Column(String(64), nullable=False, index=True)
    initial_state = Column(JSON, nullable=False, default=dict)
    future_state = Column(JSON, nullable=False, default=dict)
    diff = Column(JSON, nullable=False, default=dict)
    effects = Column(JSON, nullable=False, default=list)
    risks = Column(JSON, nullable=False, default=list)
    assumptions = Column(JSON, nullable=False, default=list)
    model_version = Column(String(64), nullable=False, default="1.0.0")
    status = Column(String(64), nullable=False, default="CREATED")
    confidence = Column(Float, nullable=False, default=1.0)
    environment_label = Column(String(64), nullable=False, default="SIMULATION_ONLY")
    is_hypothetical = Column(Boolean, nullable=False, default=True)
    provenance = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_sim_status", "status"),
        Index("ix_sim_created_at", "created_at"),
    )


class ExecutionGateModel(Base):
    __tablename__ = "simulation_execution_gates"

    id = Column(String(64), primary_key=True, default=lambda: f"gate_{uuid.uuid4().hex[:12]}")
    gate_id = Column(String(64), unique=True, nullable=False, index=True)
    simulation_id = Column(String(64), nullable=False, index=True)
    scenario_id = Column(String(64), nullable=False, index=True)
    status = Column(String(64), nullable=False, default="BLOCKED")
    baseline_snapshot_id = Column(String(64), nullable=False)
    baseline_hash_at_sim = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=True)
    drift_detected = Column(Boolean, nullable=False, default=False)
    drift_details = Column(JSON, nullable=False, default=dict)
    verification_plan = Column(JSON, nullable=False, default=list)
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_gate_status", "status"),
    )


class SimulationCalibrationModel(Base):
    __tablename__ = "simulation_calibrations"

    id = Column(String(64), primary_key=True, default=lambda: f"cal_{uuid.uuid4().hex[:12]}")
    calibration_id = Column(String(64), unique=True, nullable=False, index=True)
    simulation_id = Column(String(64), nullable=False, index=True)
    metric_name = Column(String(128), nullable=False)
    predicted_value = Column(Float, nullable=False, default=0.0)
    actual_value = Column(Float, nullable=False, default=0.0)
    error = Column(Float, nullable=False, default=0.0)
    bias = Column(Float, nullable=False, default=0.0)
    calibrated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_cal_metric", "metric_name"),
        Index("ix_cal_sim_id", "simulation_id"),
    )
