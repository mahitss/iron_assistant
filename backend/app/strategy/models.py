"""SQLAlchemy ORM models for Task 106:
Autonomous Knowledge-to-Action Learning, Strategy Synthesis & Adaptive Operating Policy Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class StrategyModel(Base):
    """Persisted Strategy entity."""
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stable_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    recommended_approach: Mapped[str] = mapped_column(Text, default="")
    current_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True)
    domain_scope: Mapped[str] = mapped_column(String(128), default="SYSTEM", index=True)
    tested_domain: Mapped[str] = mapped_column(Text, default="")
    supported_domain: Mapped[str] = mapped_column(Text, default="")
    unknown_domain: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.5)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validity_window_seconds: Mapped[int] = mapped_column(Integer, default=604800)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    provenance_type: Mapped[str] = mapped_column(String(64), default="EXPERIENCE_MINING")
    provenance_id: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyVersionModel(Base):
    """Immutable version of a strategy."""
    __tablename__ = "strategy_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    parent_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    change_description: Mapped[str] = mapped_column(Text, default="")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    rules: Mapped[list] = mapped_column(JSON, default=list)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="CANDIDATE")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    counterexample_count: Mapped[int] = mapped_column(Integer, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyConditionModel(Base):
    """Conditions under which a strategy applies."""
    __tablename__ = "strategy_conditions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    condition_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(32), default="EQUALS")
    field_path: Mapped[str] = mapped_column(String(255), nullable=False)
    target_value: Mapped[dict | list | str | int | float | bool] = mapped_column(JSON, default=dict)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyPreconditionModel(Base):
    """Hard or soft preconditions for strategy feasibility."""
    __tablename__ = "strategy_preconditions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    precondition_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requirement_description: Mapped[str] = mapped_column(Text, default="")
    verification_key: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_state: Mapped[dict | list | str | int | float | bool] = mapped_column(JSON, default=True)
    is_hard_requirement: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyContraindicationModel(Base):
    """Conditions prohibiting strategy usage."""
    __tablename__ = "strategy_contraindications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    contraindication_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="PROHIBITIVE", index=True)
    trigger_condition: Mapped[dict] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyOutcomeModel(Base):
    """Expected outcome along a performance dimension."""
    __tablename__ = "strategy_outcomes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expected_delta: Mapped[float] = mapped_column(Float, default=0.0)
    variance: Mapped[float] = mapped_column(Float, default=0.0)
    success_criteria: Mapped[str] = mapped_column(Text, default="")
    measurement_unit: Mapped[str] = mapped_column(String(32), default="percentage")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyFailureModeModel(Base):
    """Known failure modes and risk factors."""
    __tablename__ = "strategy_failure_modes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    failure_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symptom: Mapped[str] = mapped_column(Text, default="")
    known_cause: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[float] = mapped_column(Float, default=0.0)
    mitigation_strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyApplicabilityModel(Base):
    """Persisted applicability check records."""
    __tablename__ = "strategy_applicabilities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluation_context: Mapped[dict] = mapped_column(JSON, default=dict)
    applicability_status: Mapped[str] = mapped_column(String(32), default="UNCERTAIN", index=True)
    applicability_score: Mapped[float] = mapped_column(Float, default=0.0)
    blocking_reasons: Mapped[list] = mapped_column(JSON, default=list)
    uncertainty_reasons: Mapped[list] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyEvidenceModel(Base):
    """Empirical observations and counterexamples."""
    __tablename__ = "strategy_evidences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    is_counterexample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    claim: Mapped[str] = mapped_column(Text, default="")
    observed_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    environmental_context: Mapped[dict] = mapped_column(JSON, default=dict)
    capability_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    confidence_weight: Mapped[float] = mapped_column(Float, default=1.0)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    sealed_hash_sha256: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyEvaluationModel(Base):
    """Formal evaluations against holdouts and benchmarks."""
    __tablename__ = "strategy_evaluations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluator: Mapped[str] = mapped_column(String(128), default="benchmark")
    evaluation_type: Mapped[str] = mapped_column(String(64), default="BENCHMARK")
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    verdict: Mapped[str] = mapped_column(String(32), default="INCONCLUSIVE", index=True)
    holdout_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    generalization_score: Mapped[float] = mapped_column(Float, default=0.0)
    evaluation_evidence_ref: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyUsageModel(Base):
    """Decisions and missions where a strategy was queried or selected."""
    __tablename__ = "strategy_usages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mission_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    situation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    execution_context: Mapped[dict] = mapped_column(JSON, default=dict)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyFeedbackModel(Base):
    """Execution feedback and delta telemetry."""
    __tablename__ = "strategy_feedbacks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    usage_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome_status: Mapped[str] = mapped_column(String(32), default="SUCCESS", index=True)
    actual_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_vs_actual_delta: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_failure_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_cost: Mapped[float] = mapped_column(Float, default=0.0)
    user_intervention: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyConflictModel(Base):
    """Detected pairwise conflicts."""
    __tablename__ = "strategy_conflicts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_a_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy_b_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conflict_type: Mapped[str] = mapped_column(String(32), default="DIRECT", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    detected_under_context: Mapped[dict] = mapped_column(JSON, default=dict)
    resolution_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategySupersessionModel(Base):
    """Lineage supersession between versions."""
    __tablename__ = "strategy_supersessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    superseded_strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    superseding_strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    superseded_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    superseding_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    superseded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyProposalModel(Base):
    """Strategy promotion proposals."""
    __tablename__ = "strategy_proposals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    target_version: Mapped[int] = mapped_column(Integer, default=1)
    proposed_by: Mapped[str] = mapped_column(String(128), default="experience_miner")
    rationale: Mapped[str] = mapped_column(Text, default="")
    mined_patterns_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    experiment_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyReviewModel(Base):
    """Operator / Governance review decisions."""
    __tablename__ = "strategy_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(128), default="kairo_governance")
    decision: Mapped[str] = mapped_column(String(32), default="APPROVED", index=True)
    comments: Mapped[str] = mapped_column(Text, default="")
    governance_approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StrategyEventModel(Base):
    """Audit log telemetry events."""
    __tablename__ = "strategy_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    dispatched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
