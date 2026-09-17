"""Autonomous Cognitive Control Plane & Unified Operating Loop (Task 102).

Revision ID: 0070_autonomous_cognitive_control_plane_and_unified_loop
Revises: 0069_autonomous_self_model_and_capability_awareness
Create Date: 2026-09-18 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0070_autonomous_cognitive_control_plane_and_unified_loop"
down_revision: str | None = "0069_autonomous_self_model_and_capability_awareness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create control_cycles table
    op.create_table(
        "control_cycles",
        sa.Column("cycle_id", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=32), server_default="CREATED", nullable=False, index=True),
        sa.Column("priority", sa.Integer(), server_default="4", nullable=False, index=True),
        sa.Column("control_mode", sa.String(length=32), server_default="BOUNDED_AUTONOMY", nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("trigger_payload_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("coalesced_triggers_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("objective_ref", sa.String(length=64), nullable=True),
        sa.Column("mission_ref", sa.String(length=64), nullable=True),
        sa.Column("situation_ref", sa.String(length=64), nullable=True),
        sa.Column("world_state_ref", sa.String(length=64), nullable=True),
        sa.Column("self_state_ref", sa.String(length=64), nullable=True),
        sa.Column("context_ref", sa.String(length=64), nullable=True),
        sa.Column("plan_ref", sa.String(length=64), nullable=True),
        sa.Column("decision_ref", sa.String(length=64), nullable=True),
        sa.Column("action_ref", sa.String(length=64), nullable=True),
        sa.Column("verification_ref", sa.String(length=64), nullable=True),
        sa.Column("result", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("waiting_reason", sa.String(length=64), nullable=True),
        sa.Column("no_action_reason", sa.String(length=64), nullable=True),
        sa.Column("budget_consumed_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("control_cycles")
