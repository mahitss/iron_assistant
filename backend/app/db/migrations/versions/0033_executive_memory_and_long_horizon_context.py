"""Migration for Executive Memory & Long-Horizon Context Engine (Task 53).

Revision ID: 0033_executive_memory_and_long_horizon_context
Revises: 0032_continuous_learning_and_experience_consolidation
Create Date: 2026-09-13 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_executive_memory_and_long_horizon_context"
down_revision: str | None = "0032_continuous_learning_and_experience_consolidation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. executive_states
    op.create_table(
        "executive_states",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("state_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="PROJECT"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("active_projects", sa.JSON(), nullable=False),
        sa.Column("active_goals", sa.JSON(), nullable=False),
        sa.Column("active_tasks", sa.JSON(), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("open_loops", sa.JSON(), nullable=False),
        sa.Column("recent_decisions", sa.JSON(), nullable=False),
        sa.Column("recent_outcomes", sa.JSON(), nullable=False),
        sa.Column("upcoming_deadlines", sa.JSON(), nullable=False),
        sa.Column("pending_commitments", sa.JSON(), nullable=False),
        sa.Column("next_actions", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_id"),
    )
    op.create_index("ix_executive_states_scope", "executive_states", ["scope", "scope_id"])
    op.create_index("ix_executive_states_timestamp", "executive_states", ["timestamp"])

    # 2. timeline_events
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("description_reference", sa.Text(), nullable=False),
        sa.Column("impact", sa.String(length=64), nullable=False, server_default="MEDIUM"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_timeline_events_project", "timeline_events", ["project_id"])
    op.create_index("ix_timeline_events_type_ts", "timeline_events", ["event_type", "timestamp"])

    # 3. open_loops
    op.create_table(
        "open_loops",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("loop_id", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="PROJECT"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loop_id"),
    )
    op.create_index("ix_open_loops_status_priority", "open_loops", ["status", "priority"])
    op.create_index("ix_open_loops_scope", "open_loops", ["scope", "scope_id"])

    # 4. blockers
    op.create_table(
        "blockers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("blocker_id", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("affected_tasks", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="HIGH"),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("causality_evidence", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id"),
    )
    op.create_index("ix_blockers_status_severity", "blockers", ["status", "severity"])

    # 5. milestones
    op.create_table(
        "milestones",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("milestone_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("goal_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNED"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("milestone_id"),
    )
    op.create_index("ix_milestones_project_status", "milestones", ["project_id", "status"])

    # 6. executive_summaries
    op.create_table(
        "executive_summaries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("summary_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("current_brief", sa.Text(), nullable=False),
        sa.Column("recent_progress", sa.JSON(), nullable=False),
        sa.Column("open_work", sa.JSON(), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("decisions", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("next_actions", sa.JSON(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("staleness_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("summary_id"),
    )
    op.create_index("ix_executive_summaries_proj_asof", "executive_summaries", ["project_id", "as_of"])

    # 7. executive_checkpoints
    op.create_table(
        "executive_checkpoints",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("goal_id", sa.String(length=128), nullable=True),
        sa.Column("state_payload", sa.JSON(), nullable=False),
        sa.Column("progress", sa.String(length=64), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("authorization", sa.JSON(), nullable=False),
        sa.Column("next_step", sa.JSON(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkpoint_id"),
    )
    op.create_index("ix_executive_checkpoints_wf", "executive_checkpoints", ["workflow_id", "valid"])

    # 8. next_actions
    op.create_table(
        "next_actions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("action_id", sa.String(length=64), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("authorization_status", sa.String(length=64), nullable=False, server_default="REQUIRED"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RECOMMENDED"),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_id"),
    )
    op.create_index("ix_next_actions_proj_status", "next_actions", ["project_id", "status"])


def downgrade() -> None:
    op.drop_table("next_actions")
    op.drop_table("executive_checkpoints")
    op.drop_table("executive_summaries")
    op.drop_table("milestones")
    op.drop_table("blockers")
    op.drop_table("open_loops")
    op.drop_table("timeline_events")
    op.drop_table("executive_states")
