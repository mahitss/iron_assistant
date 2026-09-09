"""Migration for Kairo Autonomous Task Engine (Task 31).

Revision ID: 0011_autonomous_task_engine
Revises: 0010_experience_and_learning
Create Date: 2026-09-09 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_autonomous_task_engine"
down_revision: str | None = "0010_experience_and_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="NORMAL"),
        sa.Column("autonomy_level", sa.String(length=32), nullable=False, server_default="SUPERVISED"),
        sa.Column("parent_task_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("current_step_id", sa.String(length=64), nullable=True),
        sa.Column("active_plan_id", sa.String(length=64), nullable=True),
        sa.Column("budget", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_user_status", "tasks", ["user_id", "status"])
    op.create_index("ix_tasks_project", "tasks", ["project_id"])
    op.create_index("ix_tasks_correlation", "tasks", ["correlation_id"])

    # 2. task_plans table
    op.create_table(
        "task_plans",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("plan_hash", sa.String(length=64), nullable=False),
        sa.Column("steps_data", sa.JSON(), nullable=False),
        sa.Column("verification_criteria", sa.JSON(), nullable=False),
        sa.Column("supersedes_plan_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_plans_task_version", "task_plans", ["task_id", "version"])
    op.create_index("ix_task_plans_hash", "task_plans", ["plan_hash"])

    # 3. task_steps table
    op.create_table(
        "task_steps",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=True),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default="READ"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resources", sa.JSON(), nullable=False),
        sa.Column("result_reference", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["task_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_steps_task_seq", "task_steps", ["task_id", "sequence"])
    op.create_index("ix_task_steps_status", "task_steps", ["task_id", "status"])
    op.create_index("ix_task_steps_idempotency", "task_steps", ["idempotency_key"])

    # 4. task_checkpoints table
    op.create_table(
        "task_checkpoints",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("state_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_checkpoints_task_created", "task_checkpoints", ["task_id", "created_at"])

    # 5. task_locks table
    op.create_table(
        "task_locks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=256), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_locks_resource", "task_locks", ["resource_type", "resource_id"])
    op.create_index("ix_task_locks_task", "task_locks", ["task_id"])


def downgrade() -> None:
    op.drop_table("task_locks")
    op.drop_table("task_checkpoints")
    op.drop_table("task_steps")
    op.drop_table("task_plans")
    op.drop_table("tasks")
