"""Migration for Kairo Cognitive Planning, Reasoning, and Adaptive Decision Engine (Task 41).

Revision ID: 0021_cognitive_planning_and_reasoning
Revises: 0020_knowledge_rag_v2
Create Date: 2026-09-10 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_cognitive_planning_and_reasoning"
down_revision: str | None = "0020_knowledge_rag_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. cognitive_goals table
    op.create_table(
        "cognitive_goals",
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="USER"),
        sa.Column("goal_type", sa.String(length=32), nullable=False, server_default="OPERATIONAL"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="NORMAL"),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("goal_id"),
    )
    op.create_index("ix_cognitive_goals_user_id", "cognitive_goals", ["user_id"])
    op.create_index("ix_cognitive_goals_project_id", "cognitive_goals", ["project_id"])
    op.create_index("ix_cognitive_goals_goal_type", "cognitive_goals", ["goal_type"])
    op.create_index("ix_cognitive_goals_status", "cognitive_goals", ["status"])

    # 2. cognitive_plans table
    op.create_table(
        "cognitive_plans",
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_plan_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("reasoning_mode", sa.String(length=32), nullable=False, server_default="DECOMPOSITION"),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("scope_lock", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("cost_estimate", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["cognitive_goals.goal_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id"),
        sa.UniqueConstraint("goal_id", "version", name="uq_cognitive_plan_goal_version"),
    )
    op.create_index("ix_cognitive_plans_goal_id", "cognitive_plans", ["goal_id"])
    op.create_index("ix_cognitive_plans_user_id", "cognitive_plans", ["user_id"])
    op.create_index("ix_cognitive_plans_project_id", "cognitive_plans", ["project_id"])
    op.create_index("ix_cognitive_plans_status", "cognitive_plans", ["status"])

    # 3. cognitive_steps table
    op.create_table(
        "cognitive_steps",
        sa.Column("step_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="READ"),
        sa.Column("reversible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("verification_spec", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("output_result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["cognitive_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("step_id"),
    )
    op.create_index("ix_cognitive_steps_plan_id", "cognitive_steps", ["plan_id"])
    op.create_index("ix_cognitive_steps_status", "cognitive_steps", ["status"])

    # 4. plan_assumptions table
    op.create_table(
        "plan_assumptions",
        sa.Column("assumption_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("criticality", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("validation_method", sa.String(length=64), nullable=False, server_default="STATE_CHECK"),
        sa.Column("validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("valid", sa.Boolean(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["cognitive_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("assumption_id"),
    )
    op.create_index("ix_plan_assumptions_plan_id", "plan_assumptions", ["plan_id"])

    # 5. plan_alternatives table
    op.create_table(
        "plan_alternatives",
        sa.Column("alternative_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("tradeoffs", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["cognitive_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("alternative_id"),
    )
    op.create_index("ix_plan_alternatives_plan_id", "plan_alternatives", ["plan_id"])

    # 6. plan_traces table
    op.create_table(
        "plan_traces",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("decision_factors", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["cognitive_plans.plan_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_traces_plan_id", "plan_traces", ["plan_id"])
    op.create_index("ix_plan_traces_event_type", "plan_traces", ["event_type"])


def downgrade() -> None:
    op.drop_table("plan_traces")
    op.drop_table("plan_alternatives")
    op.drop_table("plan_assumptions")
    op.drop_table("cognitive_steps")
    op.drop_table("cognitive_plans")
    op.drop_table("cognitive_goals")
