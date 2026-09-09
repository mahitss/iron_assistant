"""Migration for Autonomous Execution, Goals, Checkpoints, and Long-Horizon Agency (Task 45).

Revision ID: 0025_autonomous_execution
Revises: 0024_multi_agent_collaboration
Create Date: 2026-09-10 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_autonomous_execution"
down_revision: str | None = "0024_multi_agent_collaboration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. autonomous_goals
    op.create_table(
        "autonomous_goals",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("hard_constraints", sa.JSON(), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autonomous_goals_user_id", "autonomous_goals", ["user_id"])
    op.create_index("ix_autonomous_goals_project_id", "autonomous_goals", ["project_id"])

    # 2. autonomous_runs
    op.create_table(
        "autonomous_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("autonomy_level", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("current_step_id", sa.String(length=64), nullable=True),
        sa.Column("progress_pct", sa.Float(), nullable=False),
        sa.Column("budget_data", sa.JSON(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checkpoint_id", sa.String(length=64), nullable=True),
        sa.Column("active_lease_id", sa.String(length=64), nullable=True),
        sa.Column("lease_owner", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["autonomous_goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autonomous_runs_goal_id", "autonomous_runs", ["goal_id"])
    op.create_index("ix_autonomous_runs_status", "autonomous_runs", ["status"])
    op.create_index("ix_autonomous_runs_owner_user_id", "autonomous_runs", ["owner_user_id"])
    op.create_index("ix_autonomous_runs_project_id", "autonomous_runs", ["project_id"])
    op.create_index("ix_autonomous_runs_owner_status", "autonomous_runs", ["owner_user_id", "status"])
    op.create_index("ix_autonomous_runs_lease", "autonomous_runs", ["active_lease_id", "lease_expires_at"])

    # 3. autonomous_checkpoints
    op.create_table(
        "autonomous_checkpoints",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=True),
        sa.Column("run_state", sa.String(length=32), nullable=False),
        sa.Column("completed_work", sa.JSON(), nullable=False),
        sa.Column("pending_work", sa.JSON(), nullable=False),
        sa.Column("active_work", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("verification_state", sa.JSON(), nullable=False),
        sa.Column("budget_state", sa.JSON(), nullable=False),
        sa.Column("world_state_version", sa.String(length=64), nullable=True),
        sa.Column("agent_state", sa.JSON(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("corruption_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["autonomous_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autonomous_checkpoints_run_id", "autonomous_checkpoints", ["run_id"])

    # 4. autonomous_completion_records
    op.create_table(
        "autonomous_completion_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("verification_results", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("remaining_uncertainty", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["autonomous_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_autonomous_completion_records_goal_id", "autonomous_completion_records", ["goal_id"])

    # 5. autonomous_journal_entries
    op.create_table(
        "autonomous_journal_entries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("sequence_num", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["autonomous_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autonomous_journal_entries_run_id", "autonomous_journal_entries", ["run_id"])
    op.create_index("ix_autonomous_journal_run_seq", "autonomous_journal_entries", ["run_id", "sequence_num"], unique=True)


def downgrade() -> None:
    op.drop_table("autonomous_journal_entries")
    op.drop_table("autonomous_completion_records")
    op.drop_table("autonomous_checkpoints")
    op.drop_table("autonomous_runs")
    op.drop_table("autonomous_goals")
