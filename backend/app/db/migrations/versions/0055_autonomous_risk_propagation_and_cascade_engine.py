"""Autonomous risk propagation, cascade analysis and systemic impact engine tables (Task 75).

Revision ID: 0055_autonomous_risk_propagation_and_cascade_engine
Revises: 0054_autonomous_forecasting_and_early_warning_engine
Create Date: 2026-09-12 01:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0055_autonomous_risk_propagation_and_cascade_engine"
down_revision: str | None = "0054_autonomous_forecasting_and_early_warning_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Propagation Analyses
    op.create_table(
        "propagation_analyses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="SERVICE", nullable=False),
        sa.Column("trigger", sa.String(length=256), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), server_default="STATE_CHANGE", nullable=False),
        sa.Column("origin_entity", sa.String(length=256), nullable=False),
        sa.Column("origin_state", sa.JSON(), nullable=False),
        sa.Column("origin_event", sa.JSON(), nullable=True),
        sa.Column("origin_forecast", sa.JSON(), nullable=True),
        sa.Column("graph_snapshot_id", sa.String(length=64), server_default="", nullable=False),
        sa.Column("causal_model_reference", sa.String(length=128), nullable=True),
        sa.Column("world_state_reference", sa.String(length=128), nullable=True),
        sa.Column("analysis_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("propagation_depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("uncertainty", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DISCOVERED", nullable=False),
        sa.Column("direct_effects", sa.JSON(), nullable=False),
        sa.Column("second_order_effects", sa.JSON(), nullable=False),
        sa.Column("resilience_assessment", sa.JSON(), nullable=False),
        sa.Column("containment_options", sa.JSON(), nullable=False),
        sa.Column("mitigation_candidates", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("is_truncated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("truncation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prop_analyses_tenant", "propagation_analyses", ["tenant_id"])
    op.create_index("ix_prop_analyses_origin", "propagation_analyses", ["origin_entity"])
    op.create_index("ix_prop_analyses_status", "propagation_analyses", ["status"])
    op.create_index("ix_prop_analyses_fingerprint", "propagation_analyses", ["fingerprint"])

    # 2. Propagation Cascades
    op.create_table(
        "propagation_cascades",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("propagation_id", sa.String(length=64), nullable=False),
        sa.Column("cascade_type", sa.String(length=32), server_default="DEPENDENCY_CASCADE", nullable=False),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("edges", sa.JSON(), nullable=False),
        sa.Column("total_depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cumulative_delay_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("amplification_detected", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("feedback_type", sa.String(length=32), server_default="STABILIZING_FEEDBACK", nullable=False),
        sa.Column("likelihood", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("impact", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DISCOVERED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prop_cascades_prop_id", "propagation_cascades", ["propagation_id"])
    op.create_index("ix_prop_cascades_fingerprint", "propagation_cascades", ["fingerprint"])

    # 3. Propagation Bottlenecks
    op.create_table(
        "propagation_bottlenecks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("propagation_id", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=256), nullable=False),
        sa.Column("name", sa.String(length=256), server_default="", nullable=False),
        sa.Column("downstream_reach", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dependency_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("centrality_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("critical_path_participant", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("resource_contention_index", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("failure_propagation_potential", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("spof_criticality", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("redundancy_state", sa.String(length=32), server_default="REDUNDANCY_UNKNOWN", nullable=False),
        sa.Column("substitutes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prop_bottlenecks_prop_id", "propagation_bottlenecks", ["propagation_id"])
    op.create_index("ix_prop_bottlenecks_entity", "propagation_bottlenecks", ["entity_id"])

    # 4. Propagation Evaluations
    op.create_table(
        "propagation_evaluations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("propagation_id", sa.String(length=64), nullable=False),
        sa.Column("target_origin", sa.String(length=256), nullable=False),
        sa.Column("predicted_nodes", sa.JSON(), nullable=False),
        sa.Column("actual_nodes", sa.JSON(), nullable=False),
        sa.Column("missed_nodes", sa.JSON(), nullable=False),
        sa.Column("false_nodes", sa.JSON(), nullable=False),
        sa.Column("node_precision", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("node_recall", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("path_precision", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("path_recall", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("depth_error", sa.Integer(), server_default="0", nullable=False),
        sa.Column("timing_error_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("impact_estimation_error", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("warning_lead_time_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("false_positive", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prop_eval_prop_id", "propagation_evaluations", ["propagation_id"])

    # 5. Propagation Snapshots
    op.create_table(
        "propagation_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("graph_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("node_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("edge_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("entities", sa.JSON(), nullable=False),
        sa.Column("relationships", sa.JSON(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prop_snapshots_tenant", "propagation_snapshots", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("propagation_snapshots")
    op.drop_table("propagation_evaluations")
    op.drop_table("propagation_bottlenecks")
    op.drop_table("propagation_cascades")
    op.drop_table("propagation_analyses")
