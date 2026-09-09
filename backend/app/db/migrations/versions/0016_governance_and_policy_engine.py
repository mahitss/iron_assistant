"""Migration for Kairo Policy, Governance, Risk, and Decision Engine (Task 36).

Revision ID: 0016_governance_and_policy_engine
Revises: 0015_unified_commands_and_intents
Create Date: 2026-09-09 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_governance_and_policy_engine"
down_revision: str | None = "0015_unified_commands_and_intents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. governance_policies table
    op.create_table(
        "governance_policies",
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("shadow_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="GLOBAL"),
        sa.Column("target_scope_id", sa.String(length=64), nullable=True),
        sa.Column("conditions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("safe_explanation", sa.Text(), nullable=True),
        sa.Column("constraints_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("policy_id"),
    )
    op.create_index("ix_governance_policies_scope", "governance_policies", ["scope"])
    op.create_index("ix_governance_policies_enabled", "governance_policies", ["enabled"])
    op.create_index("ix_governance_policies_priority", "governance_policies", ["priority"])

    # 2. policy_evaluations table
    op.create_table(
        "policy_evaluations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("environment", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=True),
        sa.Column("target", sa.String(length=256), nullable=True),
        sa.Column("tool_name", sa.String(length=64), nullable=True),
        sa.Column("skill_name", sa.String(length=64), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("safe_explanation", sa.Text(), nullable=True),
        sa.Column("constraints_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("required_approval", sa.String(length=64), nullable=True),
        sa.Column("required_authentication", sa.String(length=64), nullable=True),
        sa.Column("allowed_scope_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("matched_policies_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_evaluations_user_id", "policy_evaluations", ["user_id"])
    op.create_index("ix_policy_evaluations_decision", "policy_evaluations", ["decision"])
    op.create_index("ix_policy_evaluations_action", "policy_evaluations", ["action"])
    op.create_index("ix_policy_evaluations_created_at", "policy_evaluations", ["created_at"])


def downgrade() -> None:
    op.drop_table("policy_evaluations")
    op.drop_table("governance_policies")
