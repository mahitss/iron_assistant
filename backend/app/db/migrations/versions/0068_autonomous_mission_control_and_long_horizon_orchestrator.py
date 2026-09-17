"""Autonomous Mission Control, Long-Horizon Execution & Continuous Objective Orchestration (Task 100).

Revision ID: 0068_autonomous_mission_control_and_long_horizon_orchestrator
Revises: 0067_autonomous_situation_awareness_and_proactive_orchestrator
Create Date: 2026-09-17 22:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0068_autonomous_mission_control_and_long_horizon_orchestrator"
down_revision: str | None = "0067_autonomous_situation_awareness_and_proactive_orchestrator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Extend existing mission_records table with Task 100 fields
    with op.batch_alter_table("mission_records") as batch_op:
        batch_op.add_column(sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False))
        batch_op.add_column(sa.Column("objective", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("autonomy_level", sa.String(length=32), server_default="BOUNDED_AUTONOMY", nullable=False))
        batch_op.add_column(sa.Column("progress_confidence", sa.Float(), server_default="1.0", nullable=False))
        batch_op.add_column(sa.Column("strategic_importance", sa.Float(), server_default="0.5", nullable=False))
        batch_op.add_column(sa.Column("uncertainty", sa.Float(), server_default="0.0", nullable=False))
        batch_op.add_column(sa.Column("health_dimensions_json", sa.JSON(), server_default="{}", nullable=False))
        batch_op.add_column(sa.Column("risk_summary_json", sa.JSON(), server_default="{}", nullable=False))
        batch_op.add_column(sa.Column("active_situations_json", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("active_decisions_json", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("active_actions_json", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("active_workflows_json", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("active_agents_json", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_review_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("current_context_id", sa.String(length=64), nullable=True))

    # 2. Create mission_objectives table
    op.create_table(
        "mission_objectives",
        sa.Column("objective_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("parent_objective_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False, index=True),
        sa.Column("ordering", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_criteria_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("progress_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. Create mission_milestones table
    op.create_table(
        "mission_milestones",
        sa.Column("milestone_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("objective_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False, index=True),
        sa.Column("ordering", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dependencies_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("goal_linkage", sa.String(length=64), nullable=True),
        sa.Column("success_criteria_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("verification_criteria_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("progress_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("current_situation", sa.String(length=64), nullable=True),
        sa.Column("current_decision", sa.String(length=64), nullable=True),
        sa.Column("current_action", sa.String(length=64), nullable=True),
        sa.Column("verification_evidence_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. Create mission_assumptions table
    op.create_table(
        "mission_assumptions",
        sa.Column("assumption_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="VALID", nullable=False, index=True),
        sa.Column("dependent_milestones_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("dependent_plan_versions_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidation_reason", sa.Text(), nullable=True),
    )

    # 5. Create mission_dependencies table
    op.create_table(
        "mission_dependencies",
        sa.Column("dependency_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("dependency_type", sa.String(length=32), server_default="INTERNAL", nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="AVAILABLE", nullable=False, index=True),
        sa.Column("details_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("escalation_ref", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. Create mission_plan_versions table
    op.create_table(
        "mission_plan_versions",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("plan_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("triggering_situation_id", sa.String(length=64), nullable=True),
        sa.Column("changed_assumptions_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("changed_milestones_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("superseded_plan_id", sa.String(length=64), nullable=True),
        sa.Column("decisions_linked_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("plan_spec_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. Create mission_reviews table
    op.create_table(
        "mission_reviews",
        sa.Column("review_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("reviewer", sa.String(length=128), server_default="system", nullable=False),
        sa.Column("review_type", sa.String(length=32), server_default="SCHEDULED", nullable=False, index=True),
        sa.Column("health_dimensions_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("findings_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("recommendations_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("actions_taken_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mission_reviews")
    op.drop_table("mission_plan_versions")
    op.drop_table("mission_dependencies")
    op.drop_table("mission_assumptions")
    op.drop_table("mission_milestones")
    op.drop_table("mission_objectives")

    with op.batch_alter_table("mission_records") as batch_op:
        batch_op.drop_column("current_context_id")
        batch_op.drop_column("next_review_at")
        batch_op.drop_column("last_review_at")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("active_agents_json")
        batch_op.drop_column("active_workflows_json")
        batch_op.drop_column("active_actions_json")
        batch_op.drop_column("active_decisions_json")
        batch_op.drop_column("active_situations_json")
        batch_op.drop_column("risk_summary_json")
        batch_op.drop_column("health_dimensions_json")
        batch_op.drop_column("uncertainty")
        batch_op.drop_column("strategic_importance")
        batch_op.drop_column("progress_confidence")
        batch_op.drop_column("autonomy_level")
        batch_op.drop_column("objective")
        batch_op.drop_column("scope")
