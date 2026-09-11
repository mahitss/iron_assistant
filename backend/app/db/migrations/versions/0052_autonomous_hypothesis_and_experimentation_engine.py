"""Autonomous hypothesis, experimentation and scientific discovery engine tables (Task 72).

Revision ID: 0052_autonomous_hypothesis_and_experimentation_engine
Revises: 0051_autonomous_reasoning_and_deliberation_engine
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0052_autonomous_hypothesis_and_experimentation_engine"
down_revision: str | None = "0051_autonomous_reasoning_and_deliberation_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Discovery Sessions
    op.create_table(
        "discovery_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("discovery_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("user_id", sa.String(length=64), server_default="default_user", nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("goal_id", sa.String(length=64), nullable=True),
        sa.Column("mission_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("domain", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("conclusions_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_discovery_sessions_discovery_id", "discovery_sessions", ["discovery_id"])
    op.create_index("ix_discovery_sessions_tenant_id", "discovery_sessions", ["tenant_id"])
    op.create_index("ix_discovery_sessions_workspace_id", "discovery_sessions", ["workspace_id"])
    op.create_index("ix_discovery_sessions_user_id", "discovery_sessions", ["user_id"])
    op.create_index("ix_discovery_sessions_status", "discovery_sessions", ["status"])
    op.create_index("ix_discovery_tenant_ws", "discovery_sessions", ["tenant_id", "workspace_id"])
    op.create_index("ix_discovery_status", "discovery_sessions", ["status"])

    # 2. Discovery Research Questions
    op.create_table(
        "discovery_questions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("question_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("discovery_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("importance", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("goal_alignment", sa.String(length=128), server_default="", nullable=False),
        sa.Column("decision_relevance", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discovery_questions_question_id", "discovery_questions", ["question_id"])
    op.create_index("ix_discovery_questions_discovery_id", "discovery_questions", ["discovery_id"])

    # 3. Discovery Hypotheses
    op.create_table(
        "discovery_hypotheses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("discovery_id", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("supporting_evidence_json", sa.JSON(), nullable=False),
        sa.Column("contradicting_evidence_json", sa.JSON(), nullable=False),
        sa.Column("falsification_criteria_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CANDIDATE", nullable=False),
        sa.Column("plausibility", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("testability", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="autonomous_discovery", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discovery_hypotheses_hypothesis_id", "discovery_hypotheses", ["hypothesis_id"])
    op.create_index("ix_discovery_hypotheses_discovery_id", "discovery_hypotheses", ["discovery_id"])

    # 4. Discovery Experiments
    op.create_table(
        "discovery_experiments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("discovery_id", sa.String(length=64), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("experiment_type", sa.String(length=32), server_default="OBSERVATIONAL", nullable=False),
        sa.Column("environment", sa.String(length=32), server_default="STAGING", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="isolated", nullable=False),
        sa.Column("independent_variables_json", sa.JSON(), nullable=False),
        sa.Column("dependent_variables_json", sa.JSON(), nullable=False),
        sa.Column("control_variables_json", sa.JSON(), nullable=False),
        sa.Column("potential_confounders_json", sa.JSON(), nullable=False),
        sa.Column("baseline_json", sa.JSON(), nullable=False),
        sa.Column("expected_result", sa.Text(), server_default="", nullable=False),
        sa.Column("success_criteria_json", sa.JSON(), nullable=False),
        sa.Column("failure_criteria_json", sa.JSON(), nullable=False),
        sa.Column("falsification_criteria_json", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), server_default="LOW_RISK", nullable=False),
        sa.Column("estimated_cost", sa.Float(), server_default="0.1", nullable=False),
        sa.Column("estimated_duration_sec", sa.Integer(), server_default="60", nullable=False),
        sa.Column("expected_information_gain", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("authorization_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_authorized", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("authorized_by", sa.String(length=64), nullable=True),
        sa.Column("rollback_plan_json", sa.JSON(), nullable=False),
        sa.Column("cleanup_plan_json", sa.JSON(), nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PROPOSED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_discovery_experiments_experiment_id", "discovery_experiments", ["experiment_id"])
    op.create_index("ix_discovery_experiments_discovery_id", "discovery_experiments", ["discovery_id"])
    op.create_index("ix_discovery_experiments_status", "discovery_experiments", ["status"])

    # 5. Discovery Predictions
    op.create_table(
        "discovery_predictions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("prediction_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False),
        sa.Column("expected_direction", sa.String(length=32), server_default="decrease", nullable=False),
        sa.Column("expected_range", sa.String(length=128), server_default="", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.75", nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("is_immutable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discovery_predictions_prediction_id", "discovery_predictions", ["prediction_id"])
    op.create_index("ix_discovery_predictions_experiment_id", "discovery_predictions", ["experiment_id"])
    op.create_index("ix_discovery_predictions_hypothesis_id", "discovery_predictions", ["hypothesis_id"])

    # 6. Discovery Observations
    op.create_table(
        "discovery_observations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("observation_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("environment", sa.String(length=32), server_default="STAGING", nullable=False),
        sa.Column("measurement_metric", sa.String(length=64), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("unit", sa.String(length=32), server_default="", nullable=False),
        sa.Column("raw_reference", sa.Text(), server_default="", nullable=False),
        sa.Column("verification_state", sa.String(length=32), server_default="UNVERIFIED", nullable=False),
        sa.Column("is_simulation", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discovery_observations_observation_id", "discovery_observations", ["observation_id"])
    op.create_index("ix_discovery_observations_experiment_id", "discovery_observations", ["experiment_id"])

    # 7. Discovery Results
    op.create_table(
        "discovery_results",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("result_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("outcome", sa.String(length=32), server_default="SUPPORTED", nullable=False),
        sa.Column("prediction_vs_observation_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("effect_size", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("unexpected_anomaly_detected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("new_hypotheses_json", sa.JSON(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("invalidation_reason", sa.Text(), nullable=True),
        sa.Column("replication_status", sa.String(length=32), server_default="SINGLE_RUN", nullable=False),
        sa.Column("generalization_scope", sa.String(length=32), server_default="ENVIRONMENT_SPECIFIC", nullable=False),
        sa.Column("conclusions_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discovery_results_result_id", "discovery_results", ["result_id"])
    op.create_index("ix_discovery_results_experiment_id", "discovery_results", ["experiment_id"])
    op.create_index("ix_discovery_results_outcome", "discovery_results", ["outcome"])

    # 8. Discovery Audit Events
    op.create_table(
        "discovery_audit_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("event_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("discovery_id", sa.String(length=64), nullable=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discovery_audit_events_event_id", "discovery_audit_events", ["event_id"])
    op.create_index("ix_discovery_audit_events_discovery_id", "discovery_audit_events", ["discovery_id"])
    op.create_index("ix_discovery_audit_events_experiment_id", "discovery_audit_events", ["experiment_id"])
    op.create_index("ix_discovery_audit_events_event_type", "discovery_audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("discovery_audit_events")
    op.drop_table("discovery_results")
    op.drop_table("discovery_observations")
    op.drop_table("discovery_predictions")
    op.drop_table("discovery_experiments")
    op.drop_table("discovery_hypotheses")
    op.drop_table("discovery_questions")
    op.drop_table("discovery_sessions")
