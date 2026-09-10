"""Migration for Self-Modeling and Metacognition Engine (Task 51).

Revision ID: 0031_self_modeling_and_metacognition
Revises: 0030_personal_knowledge_graph_and_relationship_memory
Create Date: 2026-09-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_self_modeling_and_metacognition"
down_revision: str | None = "0030_personal_knowledge_graph_and_relationship_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. metacog_self_model_snapshots
    op.create_table(
        "metacog_self_model_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("limitations_json", sa.JSON(), nullable=False),
        sa.Column("resource_json", sa.JSON(), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metacog_self_model_snapshots_user_id", "metacog_self_model_snapshots", ["user_id"])
    op.create_index("ix_metacog_self_model_snapshots_created_at", "metacog_self_model_snapshots", ["created_at"])

    # 2. metacog_limitations
    op.create_table(
        "metacog_limitations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metacog_limitations_category", "metacog_limitations", ["category"])
    op.create_index("ix_metacog_limitations_user_id", "metacog_limitations", ["user_id"])

    # 3. metacog_failures
    op.create_table(
        "metacog_failures",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("failure_type", sa.String(length=32), nullable=False),
        sa.Column("cause", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("recoverability", sa.String(length=32), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metacog_failures_task_id", "metacog_failures", ["task_id"])
    op.create_index("ix_metacog_failures_user_id", "metacog_failures", ["user_id"])

    # 4. metacog_reflections
    op.create_table(
        "metacog_reflections",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("lessons_json", sa.JSON(), nullable=False),
        sa.Column("corrections_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metacog_reflections_goal_id", "metacog_reflections", ["goal_id"])
    op.create_index("ix_metacog_reflections_user_id", "metacog_reflections", ["user_id"])


def downgrade() -> None:
    op.drop_table("metacog_reflections")
    op.drop_table("metacog_failures")
    op.drop_table("metacog_limitations")
    op.drop_table("metacog_self_model_snapshots")
