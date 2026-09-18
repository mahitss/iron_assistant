"""SQLAlchemy persistence models for Task 113:
Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class CounterfactualAnalysisModel(Base):
    """Authoritative counterfactual analysis records."""

    __tablename__ = "counterfactual_analyses_t113"

    analysis_id = Column(String(64), primary_key=True)
    version = Column(Integer, default=1, nullable=False)
    target_entity = Column(String(128), nullable=False, index=True)
    question = Column(Text, nullable=False, default="")
    lifecycle_stage = Column(String(32), nullable=False, default="REQUESTED", index=True)
    counterfactual_type = Column(String(32), nullable=False, default="RESOURCE")
    baseline_id = Column(String(64), nullable=False, index=True)
    baseline_json = Column(JSON, nullable=False)
    causal_model_version = Column(String(32), nullable=False, default="v1.0")
    comparison_summary = Column(Text, nullable=False, default="")
    sensitivity_json = Column(JSON, nullable=True)
    robustness_json = Column(JSON, nullable=True)
    experiment_plan_json = Column(JSON, nullable=True)
    information_gain_proposals_json = Column(JSON, nullable=False, default=list)
    is_stale = Column(Boolean, nullable=False, default=False, index=True)
    stale_reason = Column(String(256), nullable=False, default="")
    environment_label = Column(String(32), nullable=False, default="SIMULATION_ONLY")
    is_hypothetical = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    scenarios = relationship("CounterfactualScenarioModel", back_populates="analysis", cascade="all, delete-orphan")


class CounterfactualScenarioModel(Base):
    """Scenarios evaluating candidate interventions or no-action baseline."""

    __tablename__ = "counterfactual_scenarios_t113"

    scenario_id = Column(String(64), primary_key=True)
    analysis_id = Column(String(64), ForeignKey("counterfactual_analyses_t113.analysis_id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_name = Column(String(128), nullable=False)
    is_no_action = Column(Boolean, nullable=False, default=False, index=True)
    scenario_type = Column(String(32), nullable=False, default="RESOURCE")
    prediction_json = Column(JSON, nullable=True)
    outcome_json = Column(JSON, nullable=True)
    simulation_budget_seconds = Column(Float, nullable=False, default=5.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    analysis = relationship("CounterfactualAnalysisModel", back_populates="scenarios")
    interventions = relationship("InterventionModel", back_populates="scenario", cascade="all, delete-orphan")


class InterventionModel(Base):
    """Intervention specifications associated with scenarios."""

    __tablename__ = "counterfactual_interventions_t113"

    intervention_id = Column(String(64), primary_key=True)
    scenario_id = Column(String(64), ForeignKey("counterfactual_scenarios_t113.scenario_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    target = Column(String(128), nullable=False, index=True)
    scope = Column(String(32), nullable=False, default="SERVICE")
    changes_json = Column(JSON, nullable=False)
    assumptions_json = Column(JSON, nullable=False, default=list)
    mechanisms_json = Column(JSON, nullable=False, default=list)
    risk_level = Column(String(32), nullable=False, default="LOW")
    requires_approval = Column(Boolean, nullable=False, default=False)
    is_blocked = Column(Boolean, nullable=False, default=False)
    block_reason = Column(String(256), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    scenario = relationship("CounterfactualScenarioModel", back_populates="interventions")


class InterventionComparisonModel(Base):
    """Multi-dimensional side-by-side comparison records."""

    __tablename__ = "counterfactual_comparisons_t113"

    comparison_id = Column(String(64), primary_key=True)
    analysis_id = Column(String(64), nullable=False, index=True)
    baseline_scenario_id = Column(String(64), nullable=False)
    items_json = Column(JSON, nullable=False)
    tradeoff_summary = Column(Text, nullable=False, default="")
    recommended_option = Column(String(128), nullable=True)
    no_action_viable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class InterventionVerificationModel(Base):
    """Prediction vs reality verification records following real-world execution."""

    __tablename__ = "counterfactual_verifications_t113"

    verification_id = Column(String(64), primary_key=True)
    analysis_id = Column(String(64), nullable=False, index=True)
    executed_intervention_id = Column(String(64), nullable=False, index=True)
    outcome = Column(String(32), nullable=False, default="UNRESOLVED")
    state_deviation_score = Column(Float, nullable=False, default=0.0)
    deviations_json = Column(JSON, nullable=False, default=dict)
    explanation_of_deviation = Column(Text, nullable=False, default="")
    verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
