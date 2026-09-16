"""Autonomous decision intelligence, option evaluation, policy-aware selection and decision memory engine tables (Task 94).

Revision ID: 0062_autonomous_decision_intelligence_and_decision_memory
Revises: 0061_autonomous_system_state_graph_and_self_modeling
Create Date: 2026-09-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0062_autonomous_decision_intelligence_and_decision_memory"
down_revision: str | None = "0061_autonomous_system_state_graph_and_self_modeling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. decisions_v2
    op.create_table(
        "decisions_v2",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("objective_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("decision_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PROPOSED", nullable=False),
        sa.Column("decision_type", sa.String(length=32), server_default="ACTION", nullable=False),
        sa.Column("selected_option_id", sa.String(length=64), nullable=True),
        sa.Column("certainty", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("risk_summary", sa.JSON(), nullable=False),
        sa.Column("resource_summary", sa.JSON(), nullable=False),
        sa.Column("governance_summary", sa.JSON(), nullable=False),
        sa.Column("security_summary", sa.JSON(), nullable=False),
        sa.Column("approval_summary", sa.JSON(), nullable=False),
        sa.Column("expected_outcomes", sa.JSON(), nullable=False),
        sa.Column("actual_outcomes", sa.JSON(), nullable=True),
        sa.Column("verification_status", sa.String(length=32), server_default="UNVERIFIED", nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiration_reason", sa.String(length=256), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dec2_dec_id", "decisions_v2", ["decision_id"])
    op.create_index("ix_dec2_obj_status", "decisions_v2", ["objective_id", "status"])
    op.create_index("ix_dec2_type_status", "decisions_v2", ["decision_type", "status"])
    op.create_index("ix_dec2_created", "decisions_v2", ["created_at"])

    # 2. decision_options_v2
    op.create_table(
        "decision_options_v2",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("option_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("option_type", sa.String(length=32), server_default="ACTION", nullable=False),
        sa.Column("action_reference", sa.String(length=256), nullable=True),
        sa.Column("is_feasible", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_dominated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("reversibility", sa.String(length=32), server_default="REVERSIBLE", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("scores_json", sa.JSON(), nullable=False),
        sa.Column("tradeoffs_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dopt2_option_id", "decision_options_v2", ["option_id"])
    op.create_index("ix_dopt2_dec_id", "decision_options_v2", ["decision_id"])
    op.create_index("ix_dopt2_dec_feasible", "decision_options_v2", ["decision_id", "is_feasible"])

    # 3. decision_assumptions
    op.create_table(
        "decision_assumptions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assumption_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=128), server_default="deliberation", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("impact_if_false", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dasm_assumption_id", "decision_assumptions", ["assumption_id"])
    op.create_index("ix_dasm_dec_id", "decision_assumptions", ["decision_id"])
    op.create_index("ix_dasm_dec_status", "decision_assumptions", ["decision_id", "status"])

    # 4. decision_outcomes_v2
    op.create_table(
        "decision_outcomes_v2",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("outcome_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("predicted_outcome", sa.JSON(), nullable=False),
        sa.Column("actual_outcome", sa.JSON(), nullable=False),
        sa.Column("deviation_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("execution_cost", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("verification_status", sa.String(length=32), server_default="VERIFIED", nullable=False),
        sa.Column("lessons_learned", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dout2_outcome_id", "decision_outcomes_v2", ["outcome_id"])
    op.create_index("ix_dout2_dec_id", "decision_outcomes_v2", ["decision_id"])


def downgrade() -> None:
    op.drop_table("decision_outcomes_v2")
    op.drop_table("decision_assumptions")
    op.drop_table("decision_options_v2")
    op.drop_table("decisions_v2")
