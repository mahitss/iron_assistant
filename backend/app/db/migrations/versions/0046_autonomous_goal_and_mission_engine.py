"""Autonomous goal management and self-directed mission engine tables (Task 66).

Revision ID: 0046_autonomous_goal_and_mission_engine
Revises: 0045_autonomous_world_model_and_foresight_engine
Create Date: 2026-09-11 23:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0046_autonomous_goal_and_mission_engine"
down_revision: str | None = "0045_autonomous_world_model_and_foresight_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Mission Goals
    op.create_table(
        "mission_goals",
        sa.Column("goal_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(length=64), server_default="USER", nullable=False),
        sa.Column("owner", sa.String(length=128), server_default="user", nullable=False),
        sa.Column("stakeholders_json", sa.JSON(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="5", nullable=False),
        sa.Column("importance", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("urgency", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success_criteria_json", sa.JSON(), nullable=False),
        sa.Column("failure_conditions_json", sa.JSON(), nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("resources_json", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("authority_scope", sa.String(length=64), server_default="EXECUTE_LOW_RISK", nullable=False),
        sa.Column("status", sa.String(length=64), server_default="DRAFT", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mission_goals_tenant_status", "mission_goals", ["tenant_id", "status"])
    op.create_index("ix_mission_goals_origin", "mission_goals", ["origin"])

    # 2. Mission Records
    op.create_table(
        "mission_records",
        sa.Column("mission_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("authority_scope", sa.String(length=64), server_default="EXECUTE_LOW_RISK", nullable=False),
        sa.Column("status", sa.String(length=64), server_default="DRAFT", nullable=False),
        sa.Column("health", sa.String(length=64), server_default="ON_TRACK", nullable=False),
        sa.Column("active_plan_id", sa.String(length=64), nullable=True),
        sa.Column("plan_versions_json", sa.JSON(), nullable=False),
        sa.Column("progress_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("budget_limits_json", sa.JSON(), nullable=False),
        sa.Column("budget_consumed_json", sa.JSON(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkpoints_json", sa.JSON(), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mission_records_tenant_status", "mission_records", ["tenant_id", "status"])
    op.create_index("ix_mission_records_health", "mission_records", ["health"])

    # 3. Mission Checkpoints
    op.create_table(
        "mission_checkpoints",
        sa.Column("checkpoint_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column("progress_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("risks_json", sa.JSON(), nullable=False),
        sa.Column("next_steps_json", sa.JSON(), nullable=False),
        sa.Column("verification_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mission_checkpoints_mission", "mission_checkpoints", ["mission_id"])

    # 4. Mission Blockers
    op.create_table(
        "mission_blockers",
        sa.Column("blocker_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False),
        sa.Column("blocker_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="HIGH", nullable=False),
        sa.Column("impact_score", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("owner", sa.String(length=128), server_default="system", nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="DETECTED", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mission_blockers_mission", "mission_blockers", ["mission_id"])

    # 5. Mission Postmortems
    op.create_table(
        "mission_postmortems",
        sa.Column("postmortem_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False),
        sa.Column("final_status", sa.String(length=64), nullable=False),
        sa.Column("what_worked_json", sa.JSON(), nullable=False),
        sa.Column("what_failed_json", sa.JSON(), nullable=False),
        sa.Column("unexpected_events_json", sa.JSON(), nullable=False),
        sa.Column("planning_errors_json", sa.JSON(), nullable=False),
        sa.Column("resource_problems_json", sa.JSON(), nullable=False),
        sa.Column("agent_performance_json", sa.JSON(), nullable=False),
        sa.Column("lessons_json", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mission_postmortems_mission", "mission_postmortems", ["mission_id"])

    # 6. Mission Audit Records
    op.create_table(
        "mission_audit_records",
        sa.Column("record_id", sa.String(length=64), primary_key=True),
        sa.Column("mission_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), server_default="system", nullable=False),
        sa.Column("authority", sa.String(length=64), server_default="EXECUTE_LOW_RISK", nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mission_audit_records_mission", "mission_audit_records", ["mission_id"])


def downgrade() -> None:
    op.drop_table("mission_audit_records")
    op.drop_table("mission_postmortems")
    op.drop_table("mission_blockers")
    op.drop_table("mission_checkpoints")
    op.drop_table("mission_records")
    op.drop_table("mission_goals")
