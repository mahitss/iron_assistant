"""Autonomous situational awareness, signal fusion and proactive response orchestrator tables (Task 99).

Revision ID: 0067_autonomous_situation_awareness_and_proactive_orchestrator
Revises: 0066_autonomous_world_state_reconciliation
Create Date: 2026-09-17 21:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0067_autonomous_situation_awareness_and_proactive_orchestrator"
down_revision: str | None = "0066_autonomous_world_state_reconciliation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Extend existing situations table with Task 99 fields
    with op.batch_alter_table("situations") as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("project_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("situation_type", sa.String(length=32), server_default="INCIDENT", nullable=False))
        batch_op.add_column(sa.Column("lifecycle_state", sa.String(length=32), server_default="DETECTED", nullable=False))
        batch_op.add_column(sa.Column("summary", sa.Text(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("first_signal_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_signal_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("priority", sa.Float(), server_default="0.5", nullable=False))
        batch_op.add_column(sa.Column("novelty", sa.Float(), server_default="0.5", nullable=False))
        batch_op.add_column(sa.Column("urgency", sa.Float(), server_default="0.5", nullable=False))
        batch_op.add_column(sa.Column("impact_score", sa.Float(), server_default="0.5", nullable=False))
        batch_op.add_column(sa.Column("uncertainty", sa.Float(), server_default="0.2", nullable=False))
        batch_op.add_column(sa.Column("observability_quality", sa.Float(), server_default="1.0", nullable=False))
        batch_op.add_column(sa.Column("freshness", sa.Float(), server_default="1.0", nullable=False))
        batch_op.add_column(sa.Column("affected_entities", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("affected_capabilities", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("affected_workflows", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("affected_agents", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("affected_projects", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("source_count", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("signal_count", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("correlation_score", sa.Float(), server_default="1.0", nullable=False))
        batch_op.add_column(sa.Column("duplicate_group", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("parent_situation_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("supersedes_situation_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("merged_from_ids", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("merged_into_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("split_from_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("causal_status", sa.String(length=32), server_default="CORRELATED", nullable=False))
        batch_op.add_column(sa.Column("state_reconciliation_status", sa.String(length=32), server_default="UNVERIFIED", nullable=False))
        batch_op.add_column(sa.Column("recommended_next_step", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("current_decision_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("current_action_transaction_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False))
        batch_op.create_index("ix_situations_tenant_id", ["tenant_id"])
        batch_op.create_index("ix_situations_user_id", ["user_id"])
        batch_op.create_index("ix_situations_project_id", ["project_id"])
        batch_op.create_index("ix_situations_situation_type", ["situation_type"])
        batch_op.create_index("ix_situations_lifecycle_state", ["lifecycle_state"])

    # 2. Canonical Signals Table
    op.create_table(
        "situation_signals",
        sa.Column("signal_id", sa.String(length=64), primary_key=True),
        sa.Column("situation_id", sa.String(length=64), sa.ForeignKey("situations.situation_id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("source_version", sa.String(length=32), server_default="1.0", nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signal_type", sa.String(length=128), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=True),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False),
        sa.Column("payload_ref", sa.String(length=256), nullable=True),
        sa.Column("payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("freshness", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("trust_classification", sa.String(length=64), server_default="TRUSTED_INTERNAL", nullable=False),
        sa.Column("sensitivity_classification", sa.String(length=64), server_default="INTERNAL", nullable=False),
        sa.Column("correlation_keys", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("causal_references", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("world_state_references", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("decision_action_references", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("event_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
    )
    op.create_index("ix_situation_signals_signal_id", "situation_signals", ["signal_id"])
    op.create_index("ix_situation_signals_situation_id", "situation_signals", ["situation_id"])
    op.create_index("ix_situation_signals_source_type", "situation_signals", ["source_type"])
    op.create_index("ix_situation_signals_signal_type", "situation_signals", ["signal_type"])
    op.create_index("ix_situation_signals_entity", "situation_signals", ["entity"])
    op.create_index("ix_situation_signals_trace_id", "situation_signals", ["trace_id"])
    op.create_index("ix_situation_signals_correlation_id", "situation_signals", ["correlation_id"])

    # 3. Situation Interventions Table
    op.create_table(
        "situation_interventions",
        sa.Column("intervention_id", sa.String(length=64), primary_key=True),
        sa.Column("situation_id", sa.String(length=64), sa.ForeignKey("situations.situation_id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=True),
        sa.Column("action_transaction_id", sa.String(length=64), nullable=True),
        sa.Column("action_name", sa.String(length=128), nullable=False),
        sa.Column("action_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("authorized", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("emergency_stopped", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("execution_result", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("verification_evidence", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situation_interventions_id", "situation_interventions", ["intervention_id"])
    op.create_index("ix_situation_interventions_sit_id", "situation_interventions", ["situation_id"])

    # 4. Situation Suppressions Table
    op.create_table(
        "situation_suppressions",
        sa.Column("suppression_id", sa.String(length=64), primary_key=True),
        sa.Column("situation_id", sa.String(length=64), sa.ForeignKey("situations.situation_id", ondelete="CASCADE"), nullable=False),
        sa.Column("suppressed_by", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), server_default="3600", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situation_suppressions_id", "situation_suppressions", ["suppression_id"])
    op.create_index("ix_situation_suppressions_sit_id", "situation_suppressions", ["situation_id"])

    # 5. Situation Patterns Table
    op.create_table(
        "situation_patterns",
        sa.Column("pattern_id", sa.String(length=64), primary_key=True),
        sa.Column("pattern_name", sa.String(length=128), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=False),
        sa.Column("recurrence_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("mean_interval_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("historical_situation_ids", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("trend", sa.String(length=32), server_default="STABLE", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situation_patterns_id", "situation_patterns", ["pattern_id"])
    op.create_index("ix_situation_patterns_name", "situation_patterns", ["pattern_name"])
    op.create_index("ix_situation_patterns_type", "situation_patterns", ["pattern_type"])

    # 6. Situation Contexts Table
    op.create_table(
        "situation_contexts",
        sa.Column("context_id", sa.String(length=64), primary_key=True),
        sa.Column("situation_id", sa.String(length=64), nullable=False),
        sa.Column("observations", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("related_entities", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("risk_findings", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("forecasts", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("goals", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("recent_actions", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("world_state_diffs", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("evidence_provenance", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("is_sanitized", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situation_contexts_id", "situation_contexts", ["context_id"])
    op.create_index("ix_situation_contexts_sit_id", "situation_contexts", ["situation_id"])


def downgrade() -> None:
    op.drop_table("situation_contexts")
    op.drop_table("situation_patterns")
    op.drop_table("situation_suppressions")
    op.drop_table("situation_interventions")
    op.drop_table("situation_signals")

    with op.batch_alter_table("situations") as batch_op:
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("version")
        batch_op.drop_column("current_action_transaction_id")
        batch_op.drop_column("current_decision_id")
        batch_op.drop_column("recommended_next_step")
        batch_op.drop_column("state_reconciliation_status")
        batch_op.drop_column("causal_status")
        batch_op.drop_column("split_from_id")
        batch_op.drop_column("merged_into_id")
        batch_op.drop_column("merged_from_ids")
        batch_op.drop_column("supersedes_situation_id")
        batch_op.drop_column("parent_situation_id")
        batch_op.drop_column("duplicate_group")
        batch_op.drop_column("correlation_score")
        batch_op.drop_column("signal_count")
        batch_op.drop_column("source_count")
        batch_op.drop_column("affected_projects")
        batch_op.drop_column("affected_agents")
        batch_op.drop_column("affected_workflows")
        batch_op.drop_column("affected_capabilities")
        batch_op.drop_column("affected_entities")
        batch_op.drop_column("freshness")
        batch_op.drop_column("observability_quality")
        batch_op.drop_column("uncertainty")
        batch_op.drop_column("impact_score")
        batch_op.drop_column("urgency")
        batch_op.drop_column("novelty")
        batch_op.drop_column("priority")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("resolved_at")
        batch_op.drop_column("last_signal_at")
        batch_op.drop_column("first_signal_at")
        batch_op.drop_column("summary")
        batch_op.drop_column("lifecycle_state")
        batch_op.drop_column("situation_type")
        batch_op.drop_column("project_id")
        batch_op.drop_column("user_id")
        batch_op.drop_column("tenant_id")
