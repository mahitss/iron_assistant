"""Autonomous Active Observation, Value-of-Information, Information Acquisition & Uncertainty Reduction Engine tables (Task 114).

Revision ID: 0082_autonomous_active_observation_and_value_of_information
Revises: 0081_autonomous_counterfactual_and_intervention_engine
Create Date: 2026-09-18 10:45:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0082_autonomous_active_observation_and_value_of_information"
down_revision: str | None = "0081_autonomous_counterfactual_and_intervention_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. observation_plans_t114
    op.create_table(
        "observation_plans_t114",
        sa.Column("plan_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("target_entity", sa.String(length=128), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="IDENTIFIED", nullable=False, index=True),
        sa.Column("recommended_stance", sa.String(length=32), server_default="OBSERVE", nullable=False),
        sa.Column("budget_allocated", sa.Float(), server_default="10.0", nullable=False),
        sa.Column("budget_spent", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("stop_reason", sa.String(length=64), nullable=True),
        sa.Column("is_stale", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("stale_reason", sa.String(length=256), server_default="", nullable=False),
        sa.Column("uncertainty_before_json", sa.JSON(), nullable=True),
        sa.Column("uncertainty_after_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. information_gaps_t114
    op.create_table(
        "information_gaps_t114",
        sa.Column("gap_id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), sa.ForeignKey("observation_plans_t114.plan_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("missing_information", sa.Text(), nullable=False),
        sa.Column("affected_entity", sa.String(length=128), nullable=False, index=True),
        sa.Column("affected_state", sa.String(length=128), server_default="", nullable=False),
        sa.Column("why_it_matters", sa.Text(), server_default="", nullable=False),
        sa.Column("dependent_decision_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("freshness_requirement_seconds", sa.Float(), server_default="60.0", nullable=False),
        sa.Column("is_resolved_by_existing_data", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("existing_evidence_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. observation_candidates_t114
    op.create_table(
        "observation_candidates_t114",
        sa.Column("candidate_id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), sa.ForeignKey("observation_plans_t114.plan_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("gap_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("target_source", sa.String(length=128), nullable=False),
        sa.Column("method", sa.String(length=32), server_default="PASSIVE", nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="ENTITY", nullable=False),
        sa.Column("cost_json", sa.JSON(), nullable=False),
        sa.Column("risk_json", sa.JSON(), nullable=False),
        sa.Column("value_estimate_json", sa.JSON(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("is_blocked", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("block_reason", sa.String(length=256), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. observation_outcomes_t114
    op.create_table(
        "observation_outcomes_t114",
        sa.Column("outcome_id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), sa.ForeignKey("observation_plans_t114.plan_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("provenance_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("data_payload", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("conflicts_with_existing", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("conflict_details", sa.Text(), server_default="", nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. observation_verifications_t114
    op.create_table(
        "observation_verifications_t114",
        sa.Column("verification_id", sa.String(length=64), primary_key=True),
        sa.Column("outcome_id", sa.String(length=64), sa.ForeignKey("observation_outcomes_t114.outcome_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("source_authenticated", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("schema_valid", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("freshness_valid", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("tamper_free", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("auditor", sa.String(length=64), server_default="VerificationEngine", nullable=False),
        sa.Column("verification_notes", sa.Text(), server_default="", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("observation_verifications_t114")
    op.drop_table("observation_outcomes_t114")
    op.drop_table("observation_candidates_t114")
    op.drop_table("information_gaps_t114")
    op.drop_table("observation_plans_t114")
