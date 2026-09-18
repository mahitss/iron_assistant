"""Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning Engine tables (Task 113).

Revision ID: 0081_autonomous_counterfactual_and_intervention_engine
Revises: 0080_autonomous_causal_explanation_and_root_cause_engine
Create Date: 2026-09-18 10:15:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0081_autonomous_counterfactual_and_intervention_engine"
down_revision: str | None = "0080_autonomous_causal_explanation_and_root_cause_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. counterfactual_analyses_t113
    op.create_table(
        "counterfactual_analyses_t113",
        sa.Column("analysis_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("target_entity", sa.String(length=128), nullable=False, index=True),
        sa.Column("question", sa.Text(), server_default="", nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=32), server_default="REQUESTED", nullable=False, index=True),
        sa.Column("counterfactual_type", sa.String(length=32), server_default="RESOURCE", nullable=False),
        sa.Column("baseline_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("baseline_json", sa.JSON(), nullable=False),
        sa.Column("causal_model_version", sa.String(length=32), server_default="v1.0", nullable=False),
        sa.Column("comparison_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("sensitivity_json", sa.JSON(), nullable=True),
        sa.Column("robustness_json", sa.JSON(), nullable=True),
        sa.Column("experiment_plan_json", sa.JSON(), nullable=True),
        sa.Column("information_gain_proposals_json", sa.JSON(), nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("stale_reason", sa.String(length=256), server_default="", nullable=False),
        sa.Column("environment_label", sa.String(length=32), server_default="SIMULATION_ONLY", nullable=False),
        sa.Column("is_hypothetical", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. counterfactual_scenarios_t113
    op.create_table(
        "counterfactual_scenarios_t113",
        sa.Column("scenario_id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_id", sa.String(length=64), sa.ForeignKey("counterfactual_analyses_t113.analysis_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scenario_name", sa.String(length=128), nullable=False),
        sa.Column("is_no_action", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("scenario_type", sa.String(length=32), server_default="RESOURCE", nullable=False),
        sa.Column("prediction_json", sa.JSON(), nullable=True),
        sa.Column("outcome_json", sa.JSON(), nullable=True),
        sa.Column("simulation_budget_seconds", sa.Float(), server_default="5.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. counterfactual_interventions_t113
    op.create_table(
        "counterfactual_interventions_t113",
        sa.Column("intervention_id", sa.String(length=64), primary_key=True),
        sa.Column("scenario_id", sa.String(length=64), sa.ForeignKey("counterfactual_scenarios_t113.scenario_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("target", sa.String(length=128), nullable=False, index=True),
        sa.Column("scope", sa.String(length=32), server_default="SERVICE", nullable=False),
        sa.Column("changes_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("mechanisms_json", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_blocked", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("block_reason", sa.String(length=256), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. counterfactual_comparisons_t113
    op.create_table(
        "counterfactual_comparisons_t113",
        sa.Column("comparison_id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("baseline_scenario_id", sa.String(length=64), nullable=False),
        sa.Column("items_json", sa.JSON(), nullable=False),
        sa.Column("tradeoff_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("recommended_option", sa.String(length=128), nullable=True),
        sa.Column("no_action_viable", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. counterfactual_verifications_t113
    op.create_table(
        "counterfactual_verifications_t113",
        sa.Column("verification_id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("executed_intervention_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("outcome", sa.String(length=32), server_default="UNRESOLVED", nullable=False),
        sa.Column("state_deviation_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("deviations_json", sa.JSON(), nullable=False),
        sa.Column("explanation_of_deviation", sa.Text(), server_default="", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("counterfactual_verifications_t113")
    op.drop_table("counterfactual_comparisons_t113")
    op.drop_table("counterfactual_interventions_t113")
    op.drop_table("counterfactual_scenarios_t113")
    op.drop_table("counterfactual_analyses_t113")
