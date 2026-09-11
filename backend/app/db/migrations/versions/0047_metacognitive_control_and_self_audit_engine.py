"""Metacognitive control and autonomous self-audit engine tables (Task 67).

Revision ID: 0047_metacognitive_control_and_self_audit_engine
Revises: 0046_autonomous_goal_and_mission_engine
Create Date: 2026-09-11 23:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0047_metacognitive_control_and_self_audit_engine"
down_revision: str | None = "0046_autonomous_goal_and_mission_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Self Models
    op.create_table(
        "self_models",
        sa.Column("self_model_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("limitations_json", sa.JSON(), nullable=False),
        sa.Column("active_goals_json", sa.JSON(), nullable=False),
        sa.Column("active_missions_json", sa.JSON(), nullable=False),
        sa.Column("known_dependencies_json", sa.JSON(), nullable=False),
        sa.Column("current_state", sa.String(length=64), server_default="CONFIDENT", nullable=False),
        sa.Column("uncertainties_json", sa.JSON(), nullable=False),
        sa.Column("known_failure_modes_json", sa.JSON(), nullable=False),
        sa.Column("performance_metrics_json", sa.JSON(), nullable=False),
        sa.Column("calibration", sa.String(length=64), server_default="WELL_CALIBRATED", nullable=False),
        sa.Column("resource_state_json", sa.JSON(), nullable=False),
        sa.Column("tool_state_json", sa.JSON(), nullable=False),
        sa.Column("model_state_json", sa.JSON(), nullable=False),
        sa.Column("risk_state_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_self_models_tenant", "self_models", ["tenant_id"])
    op.create_index("ix_self_models_state", "self_models", ["current_state"])

    # 2. Self Audit Beliefs
    op.create_table(
        "self_audit_beliefs",
        sa.Column("belief_id", sa.String(length=64), primary_key=True),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), server_default="ACTIVE", nullable=False),
        sa.Column("revisions_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_self_audit_beliefs_tenant_status", "self_audit_beliefs", ["tenant_id", "status"])
    op.create_index("ix_self_audit_beliefs_subject", "self_audit_beliefs", ["subject"])

    # 3. Self Audit Records
    op.create_table(
        "self_audit_records",
        sa.Column("audit_id", sa.String(length=64), primary_key=True),
        sa.Column("scope", sa.String(length=128), server_default="system", nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("audit_type", sa.String(length=64), server_default="PERIODIC", nullable=False),
        sa.Column("depth", sa.String(length=64), server_default="STANDARD", nullable=False),
        sa.Column("checks_performed_json", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="INFO", nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("recommendations_json", sa.JSON(), nullable=False),
        sa.Column("verification_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_self_audit_records_tenant_type", "self_audit_records", ["tenant_id", "audit_type"])
    op.create_index("ix_self_audit_records_severity", "self_audit_records", ["severity"])

    # 4. Self Audit Findings
    op.create_table(
        "self_audit_findings",
        sa.Column("finding_id", sa.String(length=64), primary_key=True),
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("impact", sa.Text(), server_default="", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("recommendation", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_self_audit_findings_audit", "self_audit_findings", ["audit_id"])
    op.create_index("ix_self_audit_findings_category", "self_audit_findings", ["category"])
    op.create_index("ix_self_audit_findings_status", "self_audit_findings", ["status"])

    # 5. Self Audit Baselines
    op.create_table(
        "self_audit_baselines",
        sa.Column("baseline_id", sa.String(length=64), primary_key=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("normal_mean", sa.Float(), nullable=False),
        sa.Column("normal_std", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("drift_threshold_pct", sa.Float(), server_default="30.0", nullable=False),
        sa.Column("current_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_drifting", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("drift_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_self_audit_baselines_metric", "self_audit_baselines", ["metric_name"])
    op.create_index("ix_self_audit_baselines_drifting", "self_audit_baselines", ["is_drifting"])

    # 6. Self Audit Error Clusters
    op.create_table(
        "self_audit_error_clusters",
        sa.Column("cluster_id", sa.String(length=64), primary_key=True),
        sa.Column("error_category", sa.String(length=64), nullable=False),
        sa.Column("pattern_name", sa.String(length=256), nullable=False),
        sa.Column("recurring_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("root_cause_hypothesis", sa.Text(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("sample_error_ids_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_self_audit_clusters_category", "self_audit_error_clusters", ["error_category"])
    op.create_index("ix_self_audit_clusters_tenant", "self_audit_error_clusters", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("self_audit_error_clusters")
    op.drop_table("self_audit_baselines")
    op.drop_table("self_audit_findings")
    op.drop_table("self_audit_records")
    op.drop_table("self_audit_beliefs")
    op.drop_table("self_models")
