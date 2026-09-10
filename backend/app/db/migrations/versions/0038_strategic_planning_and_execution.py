"""Migration for Strategic Planning & Long-Horizon Execution Engine (Task 58).

Revision ID: 0038_strategic_planning_and_execution
Revises: 0037_executive_decision_engine
Create Date: 2026-09-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_strategic_planning_and_execution"
down_revision: str | None = "0037_executive_decision_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. strategic_plans
    op.create_table(
        "strategic_plans",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("goal_id", sa.String(length=128), nullable=True),
        sa.Column("decision_id", sa.String(length=128), nullable=True),
        sa.Column("current_state_summary", sa.Text(), nullable=False),
        sa.Column("desired_state_summary", sa.Text(), nullable=False),
        sa.Column("strategy_type", sa.String(length=64), nullable=False, server_default="INCREMENTAL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("owner", sa.String(length=128), nullable=False, server_default="OWNER_UNASSIGNED"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id"),
    )
    op.create_index("ix_strategic_plans_plan_id", "strategic_plans", ["plan_id"])
    op.create_index("ix_strategic_plans_status_goal", "strategic_plans", ["status", "goal_id"])
    op.create_index("ix_strategic_plans_created", "strategic_plans", ["created_at"])

    # 2. plan_phases
    op.create_table(
        "plan_phases",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("phase_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phase_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNED"),
        sa.Column("entry_criteria", sa.JSON(), nullable=False),
        sa.Column("exit_criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["strategic_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phase_id"),
    )
    op.create_index("ix_plan_phases_phase_id", "plan_phases", ["phase_id"])
    op.create_index("ix_plan_phases_plan_id", "plan_phases", ["plan_id"])

    # 3. plan_milestones
    op.create_table(
        "plan_milestones",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("milestone_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("phase_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("verification_criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["strategic_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("milestone_id"),
    )
    op.create_index("ix_plan_milestones_milestone_id", "plan_milestones", ["milestone_id"])
    op.create_index("ix_plan_milestones_plan_id", "plan_milestones", ["plan_id"])

    # 4. plan_work_packages
    op.create_table(
        "plan_work_packages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("package_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("phase_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False, server_default="OWNER_UNASSIGNED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["strategic_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_id"),
    )
    op.create_index("ix_plan_work_packages_package_id", "plan_work_packages", ["package_id"])
    op.create_index("ix_plan_work_packages_plan_id", "plan_work_packages", ["plan_id"])

    # 5. plan_tasks
    op.create_table(
        "plan_tasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("phase_id", sa.String(length=64), nullable=True),
        sa.Column("package_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False, server_default="OWNER_UNASSIGNED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("resources_required", sa.JSON(), nullable=False),
        sa.Column("duration_min", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("duration_expected", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("duration_max", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column("is_irreversible", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("execution_wave", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["strategic_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_plan_tasks_task_id", "plan_tasks", ["task_id"])
    op.create_index("ix_plan_tasks_plan_id", "plan_tasks", ["plan_id"])

    # 6. plan_checkpoints
    op.create_table(
        "plan_checkpoints",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("trigger_milestone_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("expected_state", sa.JSON(), nullable=False),
        sa.Column("observed_state", sa.JSON(), nullable=False),
        sa.Column("variance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("decision_action", sa.String(length=32), nullable=False, server_default="CONTINUE"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["strategic_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkpoint_id"),
    )
    op.create_index("ix_plan_checkpoints_checkpoint_id", "plan_checkpoints", ["checkpoint_id"])
    op.create_index("ix_plan_checkpoints_plan_id", "plan_checkpoints", ["plan_id"])

    # 7. plan_revisions
    op.create_table(
        "plan_revisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("revision_id", sa.String(length=64), nullable=False),
        sa.Column("parent_plan_id", sa.String(length=64), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("diff_summary", sa.JSON(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_plan_id"], ["strategic_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id"),
    )
    op.create_index("ix_plan_revisions_revision_id", "plan_revisions", ["revision_id"])
    op.create_index("ix_plan_revisions_parent_plan_id", "plan_revisions", ["parent_plan_id"])

    # 8. plan_outcomes
    op.create_table(
        "plan_outcomes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("outcome_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("actual_duration", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimation_error", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("lessons_learned", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["strategic_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outcome_id"),
    )
    op.create_index("ix_plan_outcomes_outcome_id", "plan_outcomes", ["outcome_id"])
    op.create_index("ix_plan_outcomes_plan_id", "plan_outcomes", ["plan_id"])


def downgrade() -> None:
    op.drop_table("plan_outcomes")
    op.drop_table("plan_revisions")
    op.drop_table("plan_checkpoints")
    op.drop_table("plan_tasks")
    op.drop_table("plan_work_packages")
    op.drop_table("plan_milestones")
    op.drop_table("plan_phases")
    op.drop_table("strategic_plans")
