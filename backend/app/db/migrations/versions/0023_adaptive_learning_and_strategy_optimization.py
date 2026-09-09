"""Migration for Kairo Adaptive Learning & Strategy Optimization Engine (Task 43).

Revision ID: 0023_adaptive_learning_and_strategy_optimization
Revises: 0022_truth_verification_and_self_correction
Create Date: 2026-09-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_adaptive_learning_and_strategy_optimization"
down_revision: str | None = "0022_truth_verification_and_self_correction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. learning_experiences
    op.create_table(
        "learning_experiences",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("experience_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("goal_type", sa.String(length=64), nullable=False, server_default="GENERAL"),
        sa.Column("plan_type", sa.String(length=64), nullable=True),
        sa.Column("strategy", sa.String(length=128), nullable=False),
        sa.Column("context_reference", sa.String(length=255), nullable=True),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("observations", sa.JSON(), nullable=False),
        sa.Column("verification_result", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experience_id"),
    )
    op.create_index("ix_learning_exp_id", "learning_experiences", ["experience_id"])
    op.create_index("ix_learning_exp_outcome", "learning_experiences", ["outcome", "created_at"])
    op.create_index("ix_learning_exp_strategy", "learning_experiences", ["strategy", "outcome"])

    # 2. learning_signals
    op.create_table(
        "learning_signals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("signal_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id"),
    )
    op.create_index("ix_learning_signals_id", "learning_signals", ["signal_id"])
    op.create_index("ix_learning_signals_type", "learning_signals", ["signal_type", "created_at"])

    # 3. learning_strategies
    op.create_table(
        "learning_strategies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prerequisites", sa.JSON(), nullable=False),
        sa.Column("expected_outcome", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("failure_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("verification_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CANDIDATE"),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("strategy_id"),
    )
    op.create_index("ix_learning_strat_id", "learning_strategies", ["strategy_id"])
    op.create_index("ix_learning_strat_domain_status", "learning_strategies", ["domain", "status"])

    # 4. learning_failure_patterns
    op.create_table(
        "learning_failure_patterns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pattern_id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("affected_components", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pattern_id"),
    )
    op.create_index("ix_learning_patterns_id", "learning_failure_patterns", ["pattern_id"])
    op.create_index("ix_learning_patterns_sig", "learning_failure_patterns", ["signature"])

    # 5. learning_experiments
    op.create_table(
        "learning_experiments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNED"),
        sa.Column("baseline_strategy_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_strategy_id", sa.String(length=64), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id"),
    )
    op.create_index("ix_learning_exp_status", "learning_experiments", ["status"])

    # 6. learning_promotions
    op.create_table(
        "learning_promotions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("promotion_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("promotion_id"),
    )
    op.create_index("ix_learning_prom_strategy", "learning_promotions", ["strategy_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("learning_promotions")
    op.drop_table("learning_experiments")
    op.drop_table("learning_failure_patterns")
    op.drop_table("learning_strategies")
    op.drop_table("learning_signals")
    op.drop_table("learning_experiences")
