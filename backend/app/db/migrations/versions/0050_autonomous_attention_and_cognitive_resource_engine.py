"""Autonomous attention and cognitive resource allocation engine tables (Task 70).

Revision ID: 0050_autonomous_attention_and_cognitive_resource_engine
Revises: 0049_universal_context_and_adaptive_personalization_engine
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0050_autonomous_attention_and_cognitive_resource_engine"
down_revision: str | None = "0049_universal_context_and_adaptive_personalization_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Attention Candidates
    op.create_table(
        "attention_candidates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("attention_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), server_default="general", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("importance", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("urgency", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("risk", sa.Float(), server_default="0.3", nullable=False),
        sa.Column("relevance", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("novelty", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("change_magnitude", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("goal_alignment", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("deadline_pressure", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("dependency_impact", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("attention_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("threshold", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("current_state", sa.String(length=32), server_default="UNSEEN", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("goal_refs_json", sa.JSON(), nullable=False),
        sa.Column("mission_refs_json", sa.JSON(), nullable=False),
        sa.Column("task_refs_json", sa.JSON(), nullable=False),
        sa.Column("incident_refs_json", sa.JSON(), nullable=False),
        sa.Column("decision_refs_json", sa.JSON(), nullable=False),
        sa.Column("required_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("required_agents_json", sa.JSON(), nullable=False),
        sa.Column("required_tools_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("context_snapshot_id", sa.String(length=64), nullable=True),
        sa.Column("delegated_to", sa.String(length=64), nullable=True),
        sa.Column("delegation_history_json", sa.JSON(), nullable=False),
        sa.Column("deferral_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("aging_boost", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("interruption_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attention_candidates_attention_id", "attention_candidates", ["attention_id"])
    op.create_index("ix_attention_candidates_tenant_id", "attention_candidates", ["tenant_id"])
    op.create_index("ix_attention_candidates_workspace_id", "attention_candidates", ["workspace_id"])
    op.create_index("ix_attention_candidates_source_type", "attention_candidates", ["source_type"])
    op.create_index("ix_attention_candidates_source_id", "attention_candidates", ["source_id"])
    op.create_index("ix_attention_candidates_attention_score", "attention_candidates", ["attention_score"])
    op.create_index("ix_attention_candidates_current_state", "attention_candidates", ["current_state"])
    op.create_index(
        "ix_attn_cand_tenant_state_score",
        "attention_candidates",
        ["tenant_id", "current_state", "attention_score"],
    )
    op.create_index("ix_attn_cand_source", "attention_candidates", ["tenant_id", "source_type", "source_id"])

    # 2. Attention Snapshots
    op.create_table(
        "attention_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("mode", sa.String(length=32), server_default="NORMAL_MODE", nullable=False),
        sa.Column("current_focus_id", sa.String(length=64), nullable=True),
        sa.Column("stack_ids_json", sa.JSON(), nullable=False),
        sa.Column("queue_summary_json", sa.JSON(), nullable=False),
        sa.Column("resource_budget_json", sa.JSON(), nullable=False),
        sa.Column("active_goal_ids_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attention_snapshots_snapshot_id", "attention_snapshots", ["snapshot_id"])
    op.create_index("ix_attention_snapshots_tenant_id", "attention_snapshots", ["tenant_id"])
    op.create_index("ix_attn_snap_tenant_created", "attention_snapshots", ["tenant_id", "created_at"])

    # 3. Attention Audit Logs
    op.create_table(
        "attention_audit_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("log_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("attention_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=False),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attention_audit_logs_log_id", "attention_audit_logs", ["log_id"])
    op.create_index("ix_attention_audit_logs_tenant_id", "attention_audit_logs", ["tenant_id"])
    op.create_index("ix_attention_audit_logs_attention_id", "attention_audit_logs", ["attention_id"])
    op.create_index(
        "ix_attn_audit_tenant_attn_action",
        "attention_audit_logs",
        ["tenant_id", "attention_id", "action"],
    )


def downgrade() -> None:
    op.drop_table("attention_audit_logs")
    op.drop_table("attention_snapshots")
    op.drop_table("attention_candidates")
