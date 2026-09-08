"""Migration for Multi-Agent Orchestration tasks and structured results.

Revision ID: 0005_multi_agent
Revises: 0004_proactive
Create Date: 2026-09-08 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_multi_agent"
down_revision: str | None = "0004_proactive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. agent_tasks
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("parent_task_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("agent_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_tasks_parent_task_id", "agent_tasks", ["parent_task_id"], unique=False)
    op.create_index("ix_agent_tasks_user_id", "agent_tasks", ["user_id"], unique=False)
    op.create_index("ix_agent_tasks_session_id", "agent_tasks", ["session_id"], unique=False)
    op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"], unique=False)
    op.create_index("ix_agent_tasks_user_session", "agent_tasks", ["user_id", "session_id"], unique=False)
    op.create_index("ix_agent_tasks_user_status", "agent_tasks", ["user_id", "status"], unique=False)

    # 2. agent_task_results
    op.create_table(
        "agent_task_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("structured_output_json", sa.JSON(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("tool_calls_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_task_results_task_id", "agent_task_results", ["task_id"], unique=False)
    op.create_index("ix_agent_task_results_user_id", "agent_task_results", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_task_results_user_id", table_name="agent_task_results")
    op.drop_index("ix_agent_task_results_task_id", table_name="agent_task_results")
    op.drop_table("agent_task_results")

    op.drop_index("ix_agent_tasks_user_status", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_user_session", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_status", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_session_id", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_user_id", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_parent_task_id", table_name="agent_tasks")
    op.drop_table("agent_tasks")
