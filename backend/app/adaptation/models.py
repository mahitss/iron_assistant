"""SQLAlchemy ORM models for Task 105:
Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AdaptationProgramModel(Base):
    """Persisted bounded improvement initiative."""
    __tablename__ = "adaptation_programs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    problem_statement: Mapped[str] = mapped_column(Text, default="")
    originating_finding_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    affected_capability: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    affected_mission_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    affected_situation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    affected_decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    baseline_id: Mapped[str] = mapped_column(String(64), default="latest_golden_baseline")
    hypothesis_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    constraints_json: Mapped[list] = mapped_column(JSON, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, default=list)
    expected_benefit: Mapped[str] = mapped_column(Text, default="")
    expected_cost: Mapped[str] = mapped_column(String(128), default="")
    success_criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    safety_criteria_json: Mapped[list] = mapped_column(JSON, default=list)
    resource_budget_json: Mapped[dict] = mapped_column(JSON, default=dict)
    time_budget_seconds: Mapped[float] = mapped_column(Float, default=3600.0)
    governance_requirements_json: Mapped[list] = mapped_column(JSON, default=list)
    rollback_strategy: Mapped[str] = mapped_column(Text, default="")
    validation_strategy: Mapped[str] = mapped_column(Text, default="")
    owner_source: Mapped[str] = mapped_column(String(128), default="autonomous_adaptation_engine")
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AdaptationHypothesisModel(Base):
    """Persisted structured IF-THEN-BECAUSE hypotheses."""
    __tablename__ = "adaptation_hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    condition_change: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_references_json: Mapped[list] = mapped_column(JSON, default=list)
    counter_hypotheses_json: Mapped[list] = mapped_column(JSON, default=list)
    assumptions_json: Mapped[list] = mapped_column(JSON, default=list)
    falsification_criteria_json: Mapped[list] = mapped_column(JSON, default=list)
    measurable_outcomes_json: Mapped[dict] = mapped_column(JSON, default=dict)
    originating_finding_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentPlanModel(Base):
    """Persisted structured experiment plans."""
    __tablename__ = "experiment_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    program_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    hypothesis_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="default_eval_dataset")
    evaluation_suite_id: Mapped[str] = mapped_column(String(64), default="comprehensive_suite")
    target_metrics_json: Mapped[list] = mapped_column(JSON, default=list)
    safety_gates_json: Mapped[list] = mapped_column(JSON, default=list)
    stop_conditions_json: Mapped[list] = mapped_column(JSON, default=list)
    resource_budget_json: Mapped[dict] = mapped_column(JSON, default=dict)
    time_limit_seconds: Mapped[float] = mapped_column(Float, default=1800.0)
    min_sample_size: Mapped[int] = mapped_column(Integer, default=20)
    max_sample_size: Mapped[int] = mapped_column(Integer, default=200)
    rollback_condition: Mapped[str] = mapped_column(Text, default="")
    evidence_requirements_json: Mapped[list] = mapped_column(JSON, default=list)
    sandbox_environment: Mapped[str] = mapped_column(String(32), default="SIMULATION", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentVariantModel(Base):
    """Persisted experiment variant tied to a governed artifact."""
    __tablename__ = "experiment_variants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_type: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True)
    config_type: Mapped[str] = mapped_column(String(32), default="CONFIGURATION")
    target_artifact_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    configuration_delta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    fingerprint: Mapped[str] = mapped_column(String(64), default="", index=True)
    is_control: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentAssignmentModel(Base):
    """Persisted deterministic experiment population assignment."""
    __tablename__ = "experiment_assignments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    assignment_seed: Mapped[int] = mapped_column(Integer, default=42)
    strategy: Mapped[str] = mapped_column(String(32), default="DETERMINISTIC_MODULO")
    population: Mapped[str] = mapped_column(String(128), default="benchmark_cases")
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    variant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentRunModel(Base):
    """Persisted experiment run execution."""
    __tablename__ = "experiment_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    program_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_number: Mapped[int] = mapped_column(Integer, default=1, index=True)
    environment: Mapped[str] = mapped_column(String(32), default="SIMULATION", index=True)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    current_sample_count: Mapped[int] = mapped_column(Integer, default=0)
    target_sample_count: Mapped[int] = mapped_column(Integer, default=20)
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed_safety_gates: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentObservationModel(Base):
    """Persisted individual run execution observation."""
    __tablename__ = "experiment_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    variant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    execution_output: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    has_error: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    world_state_drift_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    decision_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentMetricModel(Base):
    """Persisted aggregated metric per variant."""
    __tablename__ = "experiment_metrics"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    variant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    variance: Mapped[float] = mapped_column(Float, default=0.0)
    standard_deviation: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_interval_low: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_interval_high: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentComparisonModel(Base):
    """Persisted tri-condition comparison."""
    __tablename__ = "experiment_comparisons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    baseline_variant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_variant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    no_action_variant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verdict: Mapped[str] = mapped_column(String(32), default="INCONCLUSIVE", index=True)
    dimension_scores_json: Mapped[dict] = mapped_column(JSON, default=dict)
    absolute_differences_json: Mapped[dict] = mapped_column(JSON, default=dict)
    relative_differences_json: Mapped[dict] = mapped_column(JSON, default=dict)
    causal_attribution_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    causal_explanation: Mapped[str] = mapped_column(Text, default="")
    world_state_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    world_state_drift_summary: Mapped[str] = mapped_column(Text, default="")
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    is_statistically_significant: Mapped[bool] = mapped_column(Boolean, default=False)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentDecisionModel(Base):
    """Persisted formal experiment decision."""
    __tablename__ = "experiment_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    comparison_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action_recommended: Mapped[str] = mapped_column(String(32), default="PROPOSE_EVOLUTION")
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_package_id: Mapped[str] = mapped_column(String(64), default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentGateModel(Base):
    """Persisted safety/security gate check for experiment execution."""
    __tablename__ = "experiment_gates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gate_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_critical_security: Mapped[bool] = mapped_column(Boolean, default=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentArtifactModel(Base):
    """Persisted experiment artifact reference."""
    __tablename__ = "experiment_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(32), default="trace", index=True)
    storage_path: Mapped[str] = mapped_column(String(255), default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExperimentEvidenceModel(Base):
    """Persisted immutable sealed evidence package."""
    __tablename__ = "experiment_evidences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    program_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hypothesis_text: Mapped[str] = mapped_column(Text, default="")
    baseline_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    candidate_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    comparison_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    observations_count: Mapped[int] = mapped_column(Integer, default=0)
    safety_gates_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    world_state_reconciled: Mapped[bool] = mapped_column(Boolean, default=True)
    resource_consumed_json: Mapped[dict] = mapped_column(JSON, default=dict)
    immutable_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvolutionProposalModel(Base):
    """Persisted formal EvolutionProposal."""
    __tablename__ = "evolution_proposals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    program_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    affected_capability: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    current_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    target_version: Mapped[str] = mapped_column(String(32), default="1.1.0")
    baseline_id: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_variant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    metrics_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    regression_results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    safety_results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    security_results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reliability_results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    resource_impact_json: Mapped[dict] = mapped_column(JSON, default=dict)
    known_limitations_json: Mapped[list] = mapped_column(JSON, default=list)
    rollback_plan: Mapped[str] = mapped_column(Text, default="")
    deployment_scope: Mapped[str] = mapped_column(String(64), default="CANARY_10_PERCENT")
    required_governance_json: Mapped[list] = mapped_column(JSON, default=list)
    required_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.85)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    parent_proposal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvolutionReviewModel(Base):
    """Persisted review on an evolution proposal."""
    __tablename__ = "evolution_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    approval_reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvolutionChangeSetModel(Base):
    """Persisted immutable ChangeSet descriptor."""
    __tablename__ = "evolution_changesets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    capability_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    current_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    candidate_version: Mapped[str] = mapped_column(String(32), default="1.1.0")
    configuration_delta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    dependencies_json: Mapped[list] = mapped_column(JSON, default=list)
    compatibility_report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    migration_requirements_json: Mapped[list] = mapped_column(JSON, default=list)
    rollback_instructions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvolutionValidationModel(Base):
    """Persisted multi-suite validation record."""
    __tablename__ = "evolution_validations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    changeset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    suite_results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    holdout_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    overall_status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    failure_details_json: Mapped[list] = mapped_column(JSON, default=list)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AdaptationEventModel(Base):
    """Persisted event audit log for lineage and timeline."""
    __tablename__ = "adaptation_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    program_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    proposal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    actor: Mapped[str] = mapped_column(String(128), default="kairo.adaptation")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
