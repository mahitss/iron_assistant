"""Autonomous Self-Model, Capability Awareness & Internal State Intelligence (Task 101).

Revision ID: 0069_autonomous_self_model_and_capability_awareness
Revises: 0068_autonomous_mission_control_and_long_horizon_orchestrator
Create Date: 2026-09-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0069_autonomous_self_model_and_capability_awareness"
down_revision: str | None = "0068_autonomous_mission_control_and_long_horizon_orchestrator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create self_model_snapshots table
    op.create_table(
        "self_model_snapshots",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("model_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("runtime_version", sa.String(length=32), server_default="0.2.0", nullable=False),
        sa.Column("protocol_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("autonomy_mode", sa.String(length=32), server_default="BOUNDED_AUTONOMY", nullable=False, index=True),
        sa.Column("emergency_stop_state", sa.Boolean(), server_default=sa.text("false"), nullable=False, index=True),
        sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("capabilities_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("tools_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("runtime_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("resources_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("security_governance_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("dependencies_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("limitations_payload", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("uncertainties_payload", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("active_missions_payload", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("active_situations_payload", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("answers_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("evidence_references", sa.JSON(), server_default="[]", nullable=False),
    )

    # 2. Create self_model_deltas table
    op.create_table(
        "self_model_deltas",
        sa.Column("delta_id", sa.String(length=64), primary_key=True),
        sa.Column("base_snapshot_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("target_snapshot_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("changes_payload", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("added_limitations", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("resolved_limitations", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("added_uncertainties", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("resolved_uncertainties", sa.JSON(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.drop_table("self_model_deltas")
    op.drop_table("self_model_snapshots")
