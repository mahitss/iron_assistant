"""Autonomous Continuous Evaluation, Benchmarking, Regression & Improvement Governance Engine (Task 104).

Revision ID: 0072_autonomous_continuous_evaluation_and_improvement_governance
Revises: 0071_autonomous_cognitive_memory_and_lifelong_learning_fabric
Create Date: 2026-09-18 01:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0072_autonomous_continuous_evaluation_and_improvement_governance"
down_revision: str | None = "0071_autonomous_cognitive_memory_and_lifelong_learning_fabric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. evaluation_suites
    op.create_table(
        "evaluation_suites",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("applicable_capabilities_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("scenario_selection_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("metric_definitions_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("thresholds_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("safety_gates_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("baseline_policy", sa.String(length=64), server_default="LATEST_GOLDEN", nullable=False),
        sa.Column("execution_mode", sa.String(length=32), server_default="REAL", nullable=False),
        sa.Column("resource_budget_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("timeout_seconds", sa.Float(), server_default="300.0", nullable=False),
        sa.Column("concurrency_limit", sa.Integer(), server_default="4", nullable=False),
        sa.Column("sampling_rate", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("holdout_policy", sa.String(length=64), server_default="EXCLUDE_UNLESS_RELEASE", nullable=False),
        sa.Column("review_required", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. evaluation_scenarios
    op.create_table(
        "evaluation_scenarios",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, index=True),
        sa.Column("scenario_class", sa.String(length=64), server_default="deterministic", nullable=False, index=True),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("initial_world_state_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("relevant_self_state_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("available_capabilities_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("available_tools_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("constraints_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("context_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("user_intent", sa.Text(), server_default="", nullable=False),
        sa.Column("environmental_conditions_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("expected_observations_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("expected_behavior", sa.Text(), server_default="", nullable=False),
        sa.Column("expected_postconditions_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("forbidden_behavior_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("safety_invariants_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("resource_budget_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("time_budget_ms", sa.Float(), server_default="30000.0", nullable=False),
        sa.Column("adversarial_conditions_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("expected_uncertainty", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_holdout", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("dataset_version", sa.String(length=32), server_default="v1.0.0", nullable=False),
        sa.Column("tags_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. evaluation_cases (legacy compatible + extended)
    op.create_table(
        "evaluation_cases",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("scenario_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("scenario_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("passed", sa.Boolean(), nullable=False, index=True),
        sa.Column("score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("duration_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("flaky", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("grader_name", sa.String(length=64), server_default="", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("grading_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("trace_sanitized_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. evaluation_datasets
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), unique=True, nullable=False, index=True),
        sa.Column("domain", sa.String(length=64), server_default="general", nullable=False, index=True),
        sa.Column("source_type", sa.String(length=64), server_default="SYNTHETIC", nullable=False),
        sa.Column("creation_reason", sa.String(length=255), server_default="benchmark", nullable=False),
        sa.Column("is_immutable", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("contamination_detected", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("case_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("golden_case_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("edge_case_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("adversarial_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_corpus_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. evaluation_dataset_versions
    op.create_table(
        "evaluation_dataset_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("dataset_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version", sa.String(length=32), nullable=False, index=True),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("case_ids_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("is_frozen", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. evaluation_fixtures
    op.create_table(
        "evaluation_fixtures",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, index=True),
        sa.Column("fixture_type", sa.String(length=64), server_default="mock", nullable=False),
        sa.Column("state_payload_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. evaluation_baselines
    op.create_table(
        "evaluation_baselines",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, index=True),
        sa.Column("baseline_type", sa.String(length=64), server_default="golden", nullable=False, index=True),
        sa.Column("version", sa.String(length=32), nullable=False, index=True),
        sa.Column("suite_id", sa.String(length=64), server_default="", nullable=False, index=True),
        sa.Column("dataset_version", sa.String(length=32), server_default="v1.0.0", nullable=False),
        sa.Column("capability_versions_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("model_version", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("environment", sa.String(length=64), server_default="staging", nullable=False),
        sa.Column("metrics_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("is_frozen", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. evaluation_runs
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("suite_name", sa.String(length=64), nullable=False, index=True),
        sa.Column("suite_id", sa.String(length=64), server_default="", nullable=False, index=True),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("kairo_version", sa.String(length=32), nullable=False, index=True),
        sa.Column("git_sha", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("pass_rate", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("security_pass_rate", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("safety_pass_rate", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("overall_quality_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("latency_p95_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("security_gate_passed", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("release_blocked", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("baseline_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("correlation_id", sa.String(length=64), server_default="", nullable=False, index=True),
        sa.Column("metrics_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("block_reasons_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("configuration_snapshot_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # 9. evaluation_run_cases
    op.create_table(
        "evaluation_run_cases",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("case_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("scenario_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("scenario_name", sa.String(length=255), nullable=False),
        sa.Column("execution_mode", sa.String(length=32), server_default="REAL", nullable=False, index=True),
        sa.Column("execution_success", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("outcome_success", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("passed", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="COMPLETED", nullable=False, index=True),
        sa.Column("duration_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("failures_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("trace_events_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("replay_reproducibility", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. evaluation_metrics
    op.create_table(
        "evaluation_metrics",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), unique=True, nullable=False, index=True),
        sa.Column("metric_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("unit", sa.String(length=32), server_default="ratio", nullable=False),
        sa.Column("direction", sa.String(length=32), server_default="HIGHER_IS_BETTER", nullable=False),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("min_sample_count", sa.Integer(), server_default="5", nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 11. evaluation_measurements
    op.create_table(
        "evaluation_measurements",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("metric_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), server_default="ratio", nullable=False),
        sa.Column("sample_size", sa.Integer(), server_default="1", nullable=False),
        sa.Column("confidence_interval_low", sa.Float(), nullable=True),
        sa.Column("confidence_interval_high", sa.Float(), nullable=True),
        sa.Column("variance", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="PASS", nullable=False, index=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 12. evaluation_comparisons
    op.create_table(
        "evaluation_comparisons",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("baseline_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("candidate_version", sa.String(length=32), nullable=False),
        sa.Column("baseline_version", sa.String(length=32), nullable=False),
        sa.Column("release_blocked", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("security_gate_passed", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("regressions_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blocking_reasons_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("deltas_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 13. evaluation_regressions
    op.create_table(
        "evaluation_regressions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("baseline_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("severity", sa.String(length=32), nullable=False, index=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("baseline_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("candidate_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("delta", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("delta_percentage", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.95", nullable=False),
        sa.Column("sample_size", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_statistically_significant", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("evidence_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("is_blocking", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("affected_capabilities_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 14. evaluation_calibration_findings
    op.create_table(
        "evaluation_calibration_findings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("subsystem", sa.String(length=64), nullable=False, index=True),
        sa.Column("brier_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("expected_calibration_error", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("overconfidence_rate", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("underconfidence_rate", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("horizon_degradation_detected", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("finding_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("is_degraded", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 15. evaluation_safety_findings
    op.create_table(
        "evaluation_safety_findings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("violation_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("severity", sa.String(length=32), server_default="CRITICAL", nullable=False, index=True),
        sa.Column("details", sa.Text(), server_default="", nullable=False),
        sa.Column("payload_sanitized_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("blocked", sa.Boolean(), server_default="1", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. evaluation_proposals
    op.create_table(
        "evaluation_proposals",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("target_area", sa.String(length=64), nullable=False, index=True),
        sa.Column("affected_capabilities_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("affected_metrics_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("baseline_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("evidence_ids_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("proposed_change_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("expected_benefit", sa.Text(), server_default="", nullable=False),
        sa.Column("expected_risks_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("resource_estimate_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("rollback_plan", sa.Text(), server_default="", nullable=False),
        sa.Column("validation_plan", sa.Text(), server_default="", nullable=False),
        sa.Column("required_approvals_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("affected_governance_policies_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PROPOSED", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 17. evaluation_experiments
    op.create_table(
        "evaluation_experiments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("control_baseline_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_configuration_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("mode", sa.String(length=32), server_default="SHADOW", nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="PLANNED", nullable=False, index=True),
        sa.Column("success_criteria_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("failure_criteria_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("safety_gates_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("sample_size_target", sa.Integer(), server_default="50", nullable=False),
        sa.Column("current_sample_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column("passed_safety_gates", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("stop_conditions_met", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 18. evaluation_evidence
    op.create_table(
        "evaluation_evidence",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("trace_events_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("world_state_snapshot_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("self_model_snapshot_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("decision_records_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("action_records_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("metrics_snapshot_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("redacted_traces_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("environment_metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("capability_fingerprint", sa.String(length=128), server_default="", nullable=False),
        sa.Column("is_sanitized", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 19. evaluation_artifacts
    op.create_table(
        "evaluation_artifacts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("artifact_name", sa.String(length=128), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), server_default="json", nullable=False),
        sa.Column("storage_path", sa.String(length=255), server_default="", nullable=False),
        sa.Column("content_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 20. evaluation_gates
    op.create_table(
        "evaluation_gates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("gate_name", sa.String(length=64), nullable=False, index=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="INCONCLUSIVE", nullable=False, index=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("measured_value", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 21. evaluation_reviews
    op.create_table(
        "evaluation_reviews",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("reviewer", sa.String(length=64), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False, index=True),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 22. evaluation_events
    op.create_table(
        "evaluation_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False, index=True),
        sa.Column("run_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("correlation_id", sa.String(length=64), server_default="", nullable=False, index=True),
        sa.Column("payload_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("evaluation_events")
    op.drop_table("evaluation_reviews")
    op.drop_table("evaluation_gates")
    op.drop_table("evaluation_artifacts")
    op.drop_table("evaluation_evidence")
    op.drop_table("evaluation_experiments")
    op.drop_table("evaluation_proposals")
    op.drop_table("evaluation_safety_findings")
    op.drop_table("evaluation_calibration_findings")
    op.drop_table("evaluation_regressions")
    op.drop_table("evaluation_comparisons")
    op.drop_table("evaluation_measurements")
    op.drop_table("evaluation_metrics")
    op.drop_table("evaluation_run_cases")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_baselines")
    op.drop_table("evaluation_fixtures")
    op.drop_table("evaluation_dataset_versions")
    op.drop_table("evaluation_datasets")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_scenarios")
    op.drop_table("evaluation_suites")
