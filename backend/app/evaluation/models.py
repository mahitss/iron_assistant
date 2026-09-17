"""SQLAlchemy ORM models for Task 104:
Autonomous Continuous Evaluation, Benchmarking, Regression & Improvement Governance Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class EvaluationSuiteModel(Base):
    """Evaluation suite specification table."""

    __tablename__ = "evaluation_suites"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", index=True)
    applicable_capabilities_json: Mapped[list] = mapped_column(JSON, default=list)
    scenario_selection_json: Mapped[list] = mapped_column(JSON, default=list)
    metric_definitions_json: Mapped[list] = mapped_column(JSON, default=list)
    thresholds_json: Mapped[dict] = mapped_column(JSON, default=dict)
    safety_gates_json: Mapped[list] = mapped_column(JSON, default=list)
    baseline_policy: Mapped[str] = mapped_column(String(64), default="LATEST_GOLDEN")
    execution_mode: Mapped[str] = mapped_column(String(32), default="REAL")
    resource_budget_json: Mapped[dict] = mapped_column(JSON, default=dict)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=300.0)
    concurrency_limit: Mapped[int] = mapped_column(Integer, default=4)
    sampling_rate: Mapped[float] = mapped_column(Float, default=1.0)
    holdout_policy: Mapped[str] = mapped_column(String(64), default="EXCLUDE_UNLESS_RELEASE")
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationScenarioModel(Base):
    """Evaluation scenario definitions."""

    __tablename__ = "evaluation_scenarios"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scenario_class: Mapped[str] = mapped_column(String(64), default="deterministic", index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    initial_world_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    relevant_self_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    objective: Mapped[str] = mapped_column(Text, default="")
    available_capabilities_json: Mapped[list] = mapped_column(JSON, default=list)
    available_tools_json: Mapped[list] = mapped_column(JSON, default=list)
    constraints_json: Mapped[list] = mapped_column(JSON, default=list)
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    user_intent: Mapped[str] = mapped_column(Text, default="")
    environmental_conditions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_observations_json: Mapped[list] = mapped_column(JSON, default=list)
    expected_behavior: Mapped[str] = mapped_column(Text, default="")
    expected_postconditions_json: Mapped[list] = mapped_column(JSON, default=list)
    forbidden_behavior_json: Mapped[list] = mapped_column(JSON, default=list)
    safety_invariants_json: Mapped[list] = mapped_column(JSON, default=list)
    resource_budget_json: Mapped[dict] = mapped_column(JSON, default=dict)
    time_budget_ms: Mapped[float] = mapped_column(Float, default=30000.0)
    adversarial_conditions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_uncertainty: Mapped[float] = mapped_column(Float, default=0.0)
    is_holdout: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(32), default="v1.0.0")
    tags_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationCaseModel(Base):
    """Persisted outcome of an individual scenario case within a dataset/run (preserves legacy compatibility)."""

    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    flaky: Mapped[bool] = mapped_column(Boolean, default=False)

    grader_name: Mapped[str] = mapped_column(String(64), default="")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    grading_json: Mapped[dict] = mapped_column(JSON, default=dict)
    trace_sanitized_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationDatasetModel(Base):
    """Versioned evaluation datasets."""

    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(64), default="general", index=True)
    source_type: Mapped[str] = mapped_column(String(64), default="SYNTHETIC")
    creation_reason: Mapped[str] = mapped_column(String(255), default="benchmark")
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=True)
    contamination_detected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    golden_case_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_case_count: Mapped[int] = mapped_column(Integer, default=0)
    adversarial_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_corpus_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationDatasetVersionModel(Base):
    """Immutable version records of evaluation datasets."""

    __tablename__ = "evaluation_dataset_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    case_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationFixtureModel(Base):
    """Evaluation mock/replay fixtures."""

    __tablename__ = "evaluation_fixtures"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fixture_type: Mapped[str] = mapped_column(String(64), default="mock")
    state_payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationBaselineModel(Base):
    """Frozen evaluation baselines."""

    __tablename__ = "evaluation_baselines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    baseline_type: Mapped[str] = mapped_column(String(64), default="golden", index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    suite_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    dataset_version: Mapped[str] = mapped_column(String(32), default="v1.0.0")
    capability_versions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(64), default="default")
    environment: Mapped[str] = mapped_column(String(64), default="staging")
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationRunModel(Base):
    """Persisted record of an evaluation or benchmark suite run."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    suite_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    suite_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    kairo_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    git_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    security_pass_rate: Mapped[float] = mapped_column(Float, default=1.0)
    safety_pass_rate: Mapped[float] = mapped_column(Float, default=1.0)
    overall_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    latency_p95_ms: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    security_gate_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    release_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    baseline_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), default="", index=True)

    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    block_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    configuration_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class EvaluationRunCaseModel(Base):
    """Detailed execution result for each case executed in a run."""

    __tablename__ = "evaluation_run_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), default="REAL", index=True)
    execution_success: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome_success: Mapped[bool] = mapped_column(Boolean, default=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", index=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    failures_json: Mapped[list] = mapped_column(JSON, default=list)
    trace_events_json: Mapped[list] = mapped_column(JSON, default=list)
    replay_reproducibility: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationMetricModel(Base):
    """Typed evaluation metric registry."""

    __tablename__ = "evaluation_metrics"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(32), default="ratio")
    direction: Mapped[str] = mapped_column(String(32), default="HIGHER_IS_BETTER")
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_sample_count: Mapped[int] = mapped_column(Integer, default=5)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationMeasurementModel(Base):
    """Measured metric records."""

    __tablename__ = "evaluation_measurements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="ratio")
    sample_size: Mapped[int] = mapped_column(Integer, default=1)
    confidence_interval_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_interval_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    variance: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PASS", index=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationComparisonModel(Base):
    """Release and baseline comparison outcomes."""

    __tablename__ = "evaluation_comparisons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    baseline_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    candidate_version: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    release_blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    security_gate_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    regressions_count: Mapped[int] = mapped_column(Integer, default=0)
    blocking_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    deltas_json: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationRegressionModel(Base):
    """Detected regression records."""

    __tablename__ = "evaluation_regressions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    baseline_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    baseline_value: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_value: Mapped[float] = mapped_column(Float, default=0.0)
    delta: Mapped[float] = mapped_column(Float, default=0.0)
    delta_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.95)
    sample_size: Mapped[int] = mapped_column(Integer, default=1)
    is_statistically_significant: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    affected_capabilities_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationCalibrationFindingModel(Base):
    """Confidence calibration degradation findings."""

    __tablename__ = "evaluation_calibration_findings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subsystem: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    brier_score: Mapped[float] = mapped_column(Float, default=0.0)
    expected_calibration_error: Mapped[float] = mapped_column(Float, default=0.0)
    overconfidence_rate: Mapped[float] = mapped_column(Float, default=0.0)
    underconfidence_rate: Mapped[float] = mapped_column(Float, default=0.0)
    horizon_degradation_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    finding_summary: Mapped[str] = mapped_column(Text, default="")
    is_degraded: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationSafetyFindingModel(Base):
    """Safety and security violation findings."""

    __tablename__ = "evaluation_safety_findings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    violation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="CRITICAL", index=True)
    details: Mapped[str] = mapped_column(Text, default="")
    payload_sanitized_json: Mapped[dict] = mapped_column(JSON, default=dict)
    blocked: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationProposalModel(Base):
    """Improvement proposals generated by evaluation."""

    __tablename__ = "evaluation_proposals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    target_area: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    affected_capabilities_json: Mapped[list] = mapped_column(JSON, default=list)
    affected_metrics_json: Mapped[list] = mapped_column(JSON, default=list)
    baseline_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    proposed_change_json: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_benefit: Mapped[str] = mapped_column(Text, default="")
    expected_risks_json: Mapped[list] = mapped_column(JSON, default=list)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.0)
    resource_estimate_json: Mapped[dict] = mapped_column(JSON, default=dict)
    rollback_plan: Mapped[str] = mapped_column(Text, default="")
    validation_plan: Mapped[str] = mapped_column(Text, default="")
    required_approvals_json: Mapped[list] = mapped_column(JSON, default=list)
    affected_governance_policies_json: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationExperimentModel(Base):
    """Controlled improvement experiments."""

    __tablename__ = "evaluation_experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    control_baseline_id: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_configuration_json: Mapped[dict] = mapped_column(JSON, default=dict)
    mode: Mapped[str] = mapped_column(String(32), default="SHADOW", index=True)
    status: Mapped[str] = mapped_column(String(32), default="PLANNED", index=True)
    success_criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    safety_gates_json: Mapped[list] = mapped_column(JSON, default=list)
    sample_size_target: Mapped[int] = mapped_column(Integer, default=50)
    current_sample_size: Mapped[int] = mapped_column(Integer, default=0)
    passed_safety_gates: Mapped[bool] = mapped_column(Boolean, default=True)
    stop_conditions_met: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationEvidenceModel(Base):
    """Immutable evidence packages."""

    __tablename__ = "evaluation_evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    trace_events_json: Mapped[list] = mapped_column(JSON, default=list)
    world_state_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    self_model_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    decision_records_json: Mapped[list] = mapped_column(JSON, default=list)
    action_records_json: Mapped[list] = mapped_column(JSON, default=list)
    metrics_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    redacted_traces_json: Mapped[list] = mapped_column(JSON, default=list)
    environment_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    capability_fingerprint: Mapped[str] = mapped_column(String(128), default="")
    is_sanitized: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationArtifactModel(Base):
    """Stored artifacts associated with runs and cases."""

    __tablename__ = "evaluation_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_name: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), default="json")
    storage_path: Mapped[str] = mapped_column(String(255), default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationGateModel(Base):
    """Evaluation gate checks."""

    __tablename__ = "evaluation_gates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gate_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="INCONCLUSIVE", index=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationReviewModel(Base):
    """Review decisions by human or governance bodies."""

    __tablename__ = "evaluation_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvaluationEventModel(Base):
    """Audit log of evaluation lifecycle events."""

    __tablename__ = "evaluation_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    proposal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
