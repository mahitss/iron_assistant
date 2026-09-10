"""Migration for Continuous Learning & Experience Consolidation Engine (Task 52).

Revision ID: 0032_continuous_learning_and_experience_consolidation
Revises: 0031_self_modeling_and_metacognition
Create Date: 2026-09-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_continuous_learning_and_experience_consolidation"
down_revision: str | None = "0031_self_modeling_and_metacognition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. learning_lessons
    op.create_table(
        "learning_lessons",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("lesson_id", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("lesson_type", sa.String(length=64), nullable=False),
        sa.Column("source_experiences", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="PROJECT"),
        sa.Column("validity", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CANDIDATE"),
        sa.Column("reinforcement_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("decay_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id"),
    )
    op.create_index("ix_learning_lessons_type_status", "learning_lessons", ["lesson_type", "status"])
    op.create_index("ix_learning_lessons_scope", "learning_lessons", ["scope"])

    # 2. learning_outcomes
    op.create_table(
        "learning_outcomes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("outcome_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("expected", sa.JSON(), nullable=False),
        sa.Column("actual", sa.JSON(), nullable=False),
        sa.Column("deviation", sa.JSON(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outcome_id"),
    )
    op.create_index("ix_learning_outcomes_task_id", "learning_outcomes", ["task_id"])
    op.create_index("ix_learning_outcomes_verified", "learning_outcomes", ["verified"])

    # 3. learning_workflows
    op.create_table(
        "learning_workflows",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("preconditions", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("expected_outcome", sa.JSON(), nullable=False),
        sa.Column("verification", sa.JSON(), nullable=False),
        sa.Column("failure_modes", sa.JSON(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CANDIDATE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id"),
    )
    op.create_index("ix_learning_workflows_status", "learning_workflows", ["status"])

    # 4. learning_heuristics
    op.create_table(
        "learning_heuristics",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("heuristic_id", sa.String(length=64), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="TASK"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CANDIDATE"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("heuristic_id"),
    )
    op.create_index("ix_learning_heuristics_scope_status", "learning_heuristics", ["scope", "status"])

    # 5. learning_replays
    op.create_table(
        "learning_replays",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("replay_id", sa.String(length=64), nullable=False),
        sa.Column("experience_id", sa.String(length=64), nullable=False),
        sa.Column("simulated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_result", sa.JSON(), nullable=False),
        sa.Column("temporal_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("leakage_detected", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("replay_id"),
    )
    op.create_index("ix_learning_replays_experience_id", "learning_replays", ["experience_id"])

    # 6. learning_policies
    op.create_table(
        "learning_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="GLOBAL"),
        sa.Column("allowed_adaptations", sa.JSON(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("rollback_policy", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id"),
    )
    op.create_index("ix_learning_policies_scope", "learning_policies", ["scope"])


def downgrade() -> None:
    op.drop_table("learning_policies")
    op.drop_table("learning_replays")
    op.drop_table("learning_heuristics")
    op.drop_table("learning_workflows")
    op.drop_table("learning_outcomes")
    op.drop_table("learning_lessons")
