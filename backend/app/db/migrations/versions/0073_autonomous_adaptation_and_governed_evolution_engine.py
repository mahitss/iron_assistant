"""Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine tables (Task 105).

Revision ID: 0073_autonomous_adaptation_and_governed_evolution_engine
Revises: 0072_autonomous_continuous_evaluation_and_improvement_governance
Create Date: 2026-09-18 01:30:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0073_autonomous_adaptation_and_governed_evolution_engine"
down_revision: str | None = "0072_autonomous_continuous_evaluation_and_improvement_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. adaptation_programs
    op.create_table(
        "adaptation_programs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False, index=True),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("problem_statement", sa.Text(), server_default="", nullable=False),
        sa.Column("originating_finding_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("affected_capability", sa.String(length=128), nullable=False, index=True),
        sa.Column("affected_mission_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("affected_situation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("affected_decision_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("baseline_id", sa.String(length=64), server_default="latest_golden_baseline", nullable=False),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("constraints_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("risks_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("expected_benefit", sa.Text(), server_default="", nullable=False),
        sa.Column("expected_cost", sa.String(length=128), server_default="", nullable=False),
        sa.Column("success_criteria_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("failure_criteria_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("safety_criteria_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("resource_budget_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("time_budget_seconds", sa.Float(), server_default="3600.0", nullable=False),
        sa.Column("governance_requirements_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("rollback_strategy", sa.Text(), server_default="", nullable=False),
        sa.Column("validation_strategy", sa.Text(), server_default="", nullable=False),
        sa.Column("owner_source", sa.String(length=128), server_default="autonomous_adaptation_engine", nullable=False),
        sa.Column("provenance_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. adaptation_hypotheses
    op.create_table(
        "adaptation_hypotheses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("condition_change", sa.Text(), nullable=False),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("evidence_reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("evidence_references_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("counter_hypotheses_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("assumptions_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("falsification_criteria_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("measurable_outcomes_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("originating_finding_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. experiment_plans
    op.create_table(
        "experiment_plans",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("program_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("dataset_id", sa.String(length=64), server_default="default_eval_dataset", nullable=False),
        sa.Column("evaluation_suite_id", sa.String(length=64), server_default="comprehensive_suite", nullable=False),
        sa.Column("target_metrics_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("safety_gates_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("stop_conditions_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("resource_budget_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("time_limit_seconds", sa.Float(), server_default="1800.0", nullable=False),
        sa.Column("min_sample_size", sa.Integer(), server_default="20", nullable=False),
        sa.Column("max_sample_size", sa.Integer(), server_default="200", nullable=False),
        sa.Column("rollback_condition", sa.Text(), server_default="", nullable=False),
        sa.Column("evidence_requirements_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("sandbox_environment", sa.String(length=32), server_default="SIMULATION", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. experiment_variants
    op.create_table(
        "experiment_variants",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("variant_type", sa.String(length=32), server_default="CANDIDATE", nullable=False, index=True),
        sa.Column("config_type", sa.String(length=32), server_default="CONFIGURATION", nullable=False),
        sa.Column("target_artifact_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("configuration_delta_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("fingerprint", sa.String(length=64), server_default="", nullable=False, index=True),
        sa.Column("is_control", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. experiment_assignments
    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("assignment_seed", sa.Integer(), server_default="42", nullable=False),
        sa.Column("strategy", sa.String(length=32), server_default="DETERMINISTIC_MODULO", nullable=False),
        sa.Column("population", sa.String(length=128), server_default="benchmark_cases", nullable=False),
        sa.Column("scenario_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("variant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. experiment_runs
    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("program_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("stage_number", sa.Integer(), server_default="1", nullable=False, index=True),
        sa.Column("environment", sa.String(length=32), server_default="SIMULATION", nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="CREATED", nullable=False, index=True),
        sa.Column("current_sample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("target_sample_count", sa.Integer(), server_default="20", nullable=False),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("passed_safety_gates", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. experiment_observations
    op.create_table(
        "experiment_observations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("variant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("scenario_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("step_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("input_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("execution_output", sa.Text(), server_default="", nullable=False),
        sa.Column("latency_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("has_error", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("world_state_drift_detected", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("decision_record_id", sa.String(length=64), nullable=True),
        sa.Column("action_transaction_id", sa.String(length=64), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. experiment_metrics
    op.create_table(
        "experiment_metrics",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("variant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("dimension", sa.String(length=32), nullable=False, index=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("metric_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("variance", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("standard_deviation", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("confidence_interval_low", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("confidence_interval_high", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. experiment_comparisons
    op.create_table(
        "experiment_comparisons",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("baseline_variant_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_variant_id", sa.String(length=64), nullable=False),
        sa.Column("no_action_variant_id", sa.String(length=64), nullable=True),
        sa.Column("verdict", sa.String(length=32), server_default="INCONCLUSIVE", nullable=False, index=True),
        sa.Column("dimension_scores_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("absolute_differences_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("relative_differences_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("causal_attribution_verified", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("causal_explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("world_state_verified", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("world_state_drift_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("sample_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_statistically_significant", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. experiment_decisions
    op.create_table(
        "experiment_decisions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("comparison_id", sa.String(length=64), nullable=False),
        sa.Column("action_recommended", sa.String(length=32), server_default="PROPOSE_EVOLUTION", nullable=False),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("evidence_package_id", sa.String(length=64), server_default="", nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 11. experiment_gates
    op.create_table(
        "experiment_gates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("gate_name", sa.String(length=64), nullable=False, index=True),
        sa.Column("passed", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("is_critical_security", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("measured_value", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 12. experiment_artifacts
    op.create_table(
        "experiment_artifacts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("artifact_type", sa.String(length=32), server_default="trace", nullable=False, index=True),
        sa.Column("storage_path", sa.String(length=255), server_default="", nullable=False),
        sa.Column("content_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 13. experiment_evidences
    op.create_table(
        "experiment_evidences",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("program_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("hypothesis_text", sa.Text(), server_default="", nullable=False),
        sa.Column("baseline_summary_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("candidate_summary_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("comparison_summary_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("observations_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("safety_gates_passed", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("world_state_reconciled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("resource_consumed_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 14. evolution_proposals
    op.create_table(
        "evolution_proposals",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("program_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("evidence_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("affected_capability", sa.String(length=128), nullable=False, index=True),
        sa.Column("current_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("target_version", sa.String(length=32), server_default="1.1.0", nullable=False),
        sa.Column("baseline_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_variant_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("metrics_summary_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("regression_results_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("safety_results_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("security_results_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("reliability_results_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("resource_impact_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("known_limitations_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("rollback_plan", sa.Text(), server_default="", nullable=False),
        sa.Column("deployment_scope", sa.String(length=64), server_default="CANARY_10_PERCENT", nullable=False),
        sa.Column("required_governance_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("required_approval", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.85", nullable=False),
        sa.Column("generation", sa.Integer(), server_default="1", nullable=False),
        sa.Column("parent_proposal_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 15. evolution_reviews
    op.create_table(
        "evolution_reviews",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("reviewer", sa.String(length=128), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False, index=True),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("approval_reference_id", sa.String(length=64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. evolution_changesets
    op.create_table(
        "evolution_changesets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("current_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("candidate_version", sa.String(length=32), server_default="1.1.0", nullable=False),
        sa.Column("configuration_delta_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("dependencies_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("compatibility_report_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("migration_requirements_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("rollback_instructions_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("content_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 17. evolution_validations
    op.create_table(
        "evolution_validations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("changeset_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("suite_results_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("holdout_passed", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("overall_status", sa.String(length=32), server_default="PENDING", nullable=False, index=True),
        sa.Column("failure_details_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 18. adaptation_events
    op.create_table(
        "adaptation_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False, index=True),
        sa.Column("program_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("correlation_id", sa.String(length=64), server_default="", nullable=False, index=True),
        sa.Column("actor", sa.String(length=128), server_default="kairo.adaptation", nullable=False),
        sa.Column("payload_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("adaptation_events")
    op.drop_table("evolution_validations")
    op.drop_table("evolution_changesets")
    op.drop_table("evolution_reviews")
    op.drop_table("evolution_proposals")
    op.drop_table("experiment_evidences")
    op.drop_table("experiment_artifacts")
    op.drop_table("experiment_gates")
    op.drop_table("experiment_decisions")
    op.drop_table("experiment_comparisons")
    op.drop_table("experiment_metrics")
    op.drop_table("experiment_observations")
    op.drop_table("experiment_runs")
    op.drop_table("experiment_assignments")
    op.drop_table("experiment_variants")
    op.drop_table("experiment_plans")
    op.drop_table("adaptation_hypotheses")
    op.drop_table("adaptation_programs")
