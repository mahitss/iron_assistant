"""Migration for Intent Understanding, Goal Extraction, and Safe Motivation Engine (Task 48).

Revision ID: 0028_intent_goal_and_motivation
Revises: 0027_predictive_intelligence
Create Date: 2026-09-10 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_intent_goal_and_motivation"
down_revision: str | None = "0027_predictive_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. user_goals
    op.create_table(
        "user_goals",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("desired_state", sa.JSON(), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("constraints_data", sa.JSON(), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False, default="NORMAL"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner", sa.String(length=64), nullable=False, default="user"),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_goals_user_id", "user_goals", ["user_id"])
    op.create_index("ix_user_goals_status", "user_goals", ["status"])
    op.create_index("ix_user_goals_intent_id", "user_goals", ["intent_id"])

    # 2. intent_objectives
    op.create_table(
        "intent_objectives",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_metric", sa.String(length=128), nullable=True),
        sa.Column("target_value", sa.String(length=128), nullable=True),
        sa.Column("is_inferred", sa.Boolean(), nullable=False, default=False),
        sa.Column("status", sa.String(length=32), nullable=False, default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intent_objectives_goal_id", "intent_objectives", ["goal_id"])

    # 3. intent_assumptions
    op.create_table(
        "intent_assumptions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, default="INFERRED"),
        sa.Column("confidence", sa.Float(), nullable=False, default=0.7),
        sa.Column("impact", sa.String(length=32), nullable=False, default="LOW"),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intent_assumptions_intent_id", "intent_assumptions", ["intent_id"])

    # 4. intent_ambiguities
    op.create_table(
        "intent_ambiguities",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("impact", sa.String(length=32), nullable=False, default="MEDIUM"),
        sa.Column("level", sa.String(length=32), nullable=False, default="MEDIUM"),
        sa.Column("resolution", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, default="UNRESOLVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intent_ambiguities_intent_id", "intent_ambiguities", ["intent_id"])

    # 5. intent_clarifications
    op.create_table(
        "intent_clarifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("affected_decision", sa.String(length=256), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("default_if_any", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, default="PENDING"),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intent_clarifications_intent_id", "intent_clarifications", ["intent_id"])

    # 6. intent_motivations
    op.create_table(
        "intent_motivations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, default=0.8),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intent_motivations_user_id", "intent_motivations", ["user_id"])

    # 7. intent_graphs
    op.create_table(
        "intent_graphs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=True),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("edges", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intent_graphs_intent_id", "intent_graphs", ["intent_id"])


def downgrade() -> None:
    op.drop_table("intent_graphs")
    op.drop_table("intent_motivations")
    op.drop_table("intent_clarifications")
    op.drop_table("intent_ambiguities")
    op.drop_table("intent_assumptions")
    op.drop_table("intent_objectives")
    op.drop_table("user_goals")
