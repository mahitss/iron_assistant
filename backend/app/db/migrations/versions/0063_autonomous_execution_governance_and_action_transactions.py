"""Autonomous execution governance, action transaction, pre-flight validation and commit/rollback tables (Task 95).

Revision ID: 0063_autonomous_execution_governance_and_action_transactions
Revises: 0062_autonomous_decision_intelligence_and_decision_memory
Create Date: 2026-09-17 01:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0063_autonomous_execution_governance_and_action_transactions"
down_revision: str | None = "0062_autonomous_decision_intelligence_and_decision_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. action_transactions
    op.create_table(
        "action_transactions",
        sa.Column("transaction_id", sa.String(length=64), primary_key=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("workflow_id", sa.String(length=64), nullable=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("capability_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("action_reference", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("target_json", sa.JSON(), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("authorization_reference", sa.String(length=128), nullable=True),
        sa.Column("approval_reference", sa.String(length=128), nullable=True),
        sa.Column("governance_reference", sa.String(length=128), nullable=True),
        sa.Column("resource_reference", sa.String(length=128), nullable=True),
        sa.Column("preflight_checks_json", sa.JSON(), nullable=False),
        sa.Column("observations_json", sa.JSON(), nullable=False),
        sa.Column("postconditions_json", sa.JSON(), nullable=False),
        sa.Column("verification_state", sa.String(length=32), server_default="NOT_STARTED", nullable=False),
        sa.Column("outcome_type", sa.String(length=32), nullable=True),
        sa.Column("outcome_summary_json", sa.JSON(), nullable=False),
        sa.Column("deviation_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("regret_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("user_id", sa.String(length=64), server_default="default_user", nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_action_txn_tx_id", "action_transactions", ["transaction_id"])
    op.create_index("ix_action_txn_dec_id", "action_transactions", ["decision_id"])
    op.create_index("ix_action_txn_status", "action_transactions", ["status"])
    op.create_index("ix_action_txn_idemp", "action_transactions", ["idempotency_key"])
    op.create_index("ix_action_txn_status_created", "action_transactions", ["status", "created_at"])
    op.create_index("ix_action_txn_decision_status", "action_transactions", ["decision_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_action_txn_decision_status", table_name="action_transactions")
    op.drop_index("ix_action_txn_status_created", table_name="action_transactions")
    op.drop_index("ix_action_txn_idemp", table_name="action_transactions")
    op.drop_index("ix_action_txn_status", table_name="action_transactions")
    op.drop_index("ix_action_txn_dec_id", table_name="action_transactions")
    op.drop_index("ix_action_txn_tx_id", table_name="action_transactions")
    op.drop_table("action_transactions")
