"""Migration for Executive Decision Engine (Task 57).

Revision ID: 0037_executive_decision_engine
Revises: 0036_simulation_and_counterfactual_planning
Create Date: 2026-09-15 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_executive_decision_engine"
down_revision: str | None = "0036_simulation_and_counterfactual_planning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. decision_requests
    op.create_table(
        "decision_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=128), nullable=True),
        sa.Column("context_scope", sa.String(length=64), nullable=False, server_default="PROJECT"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("authority", sa.String(length=128), nullable=False, server_default="user"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_tolerance", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="ANALYZING"),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_decision_requests_request_id", "decision_requests", ["request_id"])
    op.create_index("ix_dreq_scope_status", "decision_requests", ["context_scope", "status"])

    # 2. decision_records
    op.create_table(
        "decision_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="RECOMMENDED"),
        sa.Column("recommendation", sa.JSON(), nullable=False),
        sa.Column("selected_option_id", sa.String(length=64), nullable=True),
        sa.Column("selected_by", sa.String(length=128), nullable=True),
        sa.Column("user_override", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("ranking", sa.JSON(), nullable=False),
        sa.Column("decision_gates", sa.JSON(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("execution_plan", sa.JSON(), nullable=True),
        sa.Column("verification_plan", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id"),
    )
    op.create_index("ix_decision_records_decision_id", "decision_records", ["decision_id"])
    op.create_index("ix_decision_records_request_id", "decision_records", ["request_id"])
    op.create_index("ix_drec_status_created", "decision_records", ["status", "created_at"])

    # 3. decision_options
    op.create_table(
        "decision_options",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("option_id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("option_type", sa.String(length=64), nullable=False, server_default="STANDARD"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_feasible", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("rejection_reason", sa.String(length=256), nullable=True),
        sa.Column("reversibility", sa.String(length=64), nullable=False, server_default="REVERSIBLE"),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("tradeoffs", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("option_id"),
    )
    op.create_index("ix_decision_options_option_id", "decision_options", ["option_id"])
    op.create_index("ix_decision_options_decision_id", "decision_options", ["decision_id"])
    op.create_index("ix_dopt_dec_score", "decision_options", ["decision_id", "score"])

    # 4. decision_commitments
    op.create_table(
        "decision_commitments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("commitment_id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="PROPOSED"),
        sa.Column("authorized_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("commitment_id"),
    )
    op.create_index("ix_decision_commitments_commitment_id", "decision_commitments", ["commitment_id"])
    op.create_index("ix_decision_commitments_decision_id", "decision_commitments", ["decision_id"])
    op.create_index("ix_dcom_status", "decision_commitments", ["status"])

    # 5. decision_outcomes
    op.create_table(
        "decision_outcomes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("outcome_id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("actual_benefit", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_duration", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("prediction_error", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("unexpected_side_effects", sa.JSON(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outcome_id"),
    )
    op.create_index("ix_decision_outcomes_outcome_id", "decision_outcomes", ["outcome_id"])
    op.create_index("ix_dout_dec_id", "decision_outcomes", ["decision_id"])

    # 6. decision_revisions
    op.create_table(
        "decision_revisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("revision_id", sa.String(length=64), nullable=False),
        sa.Column("parent_decision_id", sa.String(length=64), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("previous_snapshot", sa.JSON(), nullable=False),
        sa.Column("new_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id"),
    )
    op.create_index("ix_decision_revisions_revision_id", "decision_revisions", ["revision_id"])
    op.create_index("ix_drev_parent_num", "decision_revisions", ["parent_decision_id", "revision_number"])


def downgrade() -> None:
    op.drop_table("decision_revisions")
    op.drop_table("decision_outcomes")
    op.drop_table("decision_commitments")
    op.drop_table("decision_options")
    op.drop_table("decision_records")
    op.drop_table("decision_requests")
