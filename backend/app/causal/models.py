"""SQLAlchemy ORM models for Kairo Causal Reasoning & Causal Graph Engine (Task 55)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String, Text

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CausalGraphModel(Base):
    __tablename__ = "causal_graphs"

    id = Column(String(64), primary_key=True, default=lambda: f"cgr_{uuid.uuid4().hex[:12]}")
    graph_id = Column(String(64), unique=True, nullable=False, index=True)
    scope = Column(String(64), nullable=False, default="SYSTEM")
    scope_id = Column(String(128), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    nodes = Column(JSON, nullable=False, default=dict)
    edges = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=1.0)
    provenance = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_cgr_scope_idx", "scope", "scope_id"),
        Index("ix_cgr_timestamp_idx", "timestamp"),
    )


class CausalNodeModel(Base):
    __tablename__ = "causal_nodes"

    id = Column(String(64), primary_key=True, default=lambda: f"cnode_{uuid.uuid4().hex[:12]}")
    node_id = Column(String(128), unique=True, nullable=False, index=True)
    entity = Column(String(128), nullable=False)
    variable = Column(String(128), nullable=False)
    state = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    source = Column(String(128), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_cnode_ent_var_idx", "entity", "variable"),
        Index("ix_cnode_ts_idx", "timestamp"),
    )


class CausalEdgeModel(Base):
    __tablename__ = "causal_edges"

    id = Column(String(64), primary_key=True, default=lambda: f"cedge_{uuid.uuid4().hex[:12]}")
    edge_id = Column(String(128), unique=True, nullable=False, index=True)
    cause = Column(String(128), nullable=False)
    effect = Column(String(128), nullable=False)
    relationship = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    evidence_refs = Column(JSON, nullable=False, default=list)
    scope = Column(String(64), nullable=False, default="SYSTEM")
    valid_from = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(64), nullable=False, default="CANDIDATE")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_cedge_cause_effect_idx", "cause", "effect"),
        Index("ix_cedge_rel_status_idx", "relationship", "status"),
    )


class CausalHypothesisModel(Base):
    __tablename__ = "causal_hypotheses"

    id = Column(String(64), primary_key=True, default=lambda: f"chyp_{uuid.uuid4().hex[:12]}")
    hypothesis_id = Column(String(64), unique=True, nullable=False, index=True)
    cause = Column(String(128), nullable=False)
    effect = Column(String(128), nullable=False)
    mechanism = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    alternatives = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.5)
    status = Column(String(64), nullable=False, default="PROPOSED")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_chyp_cause_effect_idx", "cause", "effect"),
        Index("ix_chyp_status_idx", "status"),
    )


class CausalEvidenceModel(Base):
    __tablename__ = "causal_evidence"

    id = Column(String(64), primary_key=True, default=lambda: f"cevid_{uuid.uuid4().hex[:12]}")
    evidence_id = Column(String(64), unique=True, nullable=False, index=True)
    type = Column(String(64), nullable=False)
    source = Column(String(128), nullable=False)
    observation = Column(JSON, nullable=False, default=dict)
    strength = Column(String(64), nullable=False, default="MODERATE")
    independence = Column(Float, nullable=False, default=1.0)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_cevid_type_idx", "type"),
        Index("ix_cevid_ts_idx", "timestamp"),
    )


class RootCauseAnalysisModel(Base):
    __tablename__ = "root_cause_analyses"

    id = Column(String(64), primary_key=True, default=lambda: f"rca_{uuid.uuid4().hex[:12]}")
    analysis_id = Column(String(64), unique=True, nullable=False, index=True)
    incident_id = Column(String(64), nullable=False, index=True)
    candidate_causes = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=list)
    eliminated_causes = Column(JSON, nullable=False, default=list)
    surviving_causes = Column(JSON, nullable=False, default=list)
    root_cause = Column(String(256), nullable=True)
    contributing_factors = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.5)
    status = Column(String(64), nullable=False, default="INVESTIGATING")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        Index("ix_rca_inc_status_idx", "incident_id", "status"),
    )


class CausalInterventionModel(Base):
    __tablename__ = "causal_interventions"

    id = Column(String(64), primary_key=True, default=lambda: f"cint_{uuid.uuid4().hex[:12]}")
    intervention_id = Column(String(64), unique=True, nullable=False, index=True)
    target = Column(String(128), nullable=False, index=True)
    change = Column(JSON, nullable=False, default=dict)
    expected_effect = Column(JSON, nullable=False, default=dict)
    actual_effect = Column(JSON, nullable=True)
    authorization = Column(JSON, nullable=False, default=dict)
    risk = Column(String(64), nullable=False, default="MEDIUM")
    verification_plan = Column(JSON, nullable=False, default=list)
    status = Column(String(64), nullable=False, default="PROPOSED")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_cint_status_idx", "status"),
    )


class CounterfactualModel(Base):
    __tablename__ = "counterfactual_scenarios"

    id = Column(String(64), primary_key=True, default=lambda: f"ccf_{uuid.uuid4().hex[:12]}")
    scenario_id = Column(String(64), unique=True, nullable=False, index=True)
    baseline = Column(JSON, nullable=False, default=dict)
    intervention = Column(JSON, nullable=False, default=dict)
    expected_difference = Column(JSON, nullable=False, default=dict)
    assumptions = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.5)
    is_hypothetical = Column(Boolean, nullable=False, default=True)
    status = Column(String(64), nullable=False, default="GENERATED")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_ccf_status_idx", "status"),
    )


class CausalExperimentModel(Base):
    __tablename__ = "causal_experiments"

    id = Column(String(64), primary_key=True, default=lambda: f"cexp_{uuid.uuid4().hex[:12]}")
    experiment_id = Column(String(64), unique=True, nullable=False, index=True)
    hypothesis_id = Column(String(64), nullable=False, index=True)
    treatment = Column(JSON, nullable=False, default=dict)
    control = Column(JSON, nullable=False, default=dict)
    metric = Column(String(128), nullable=False)
    duration_seconds = Column(Integer, nullable=False, default=300)
    authorization = Column(JSON, nullable=False, default=dict)
    status = Column(String(64), nullable=False, default="PENDING_APPROVAL")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_cexp_status_idx", "status"),
    )
