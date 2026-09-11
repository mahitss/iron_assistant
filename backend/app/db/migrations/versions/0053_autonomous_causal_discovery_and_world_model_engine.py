"""Autonomous causal discovery and world-model learning engine tables (Task 73).

Revision ID: 0053_autonomous_causal_discovery_and_world_model_engine
Revises: 0052_autonomous_hypothesis_and_experimentation_engine
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0053_autonomous_causal_discovery_and_world_model_engine"
down_revision: str | None = "0052_autonomous_hypothesis_and_experimentation_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Causal Relationships
    op.create_table(
        "causal_relationships",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("relation_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("cause_entity", sa.String(length=128), nullable=False),
        sa.Column("cause_variable", sa.String(length=128), nullable=False),
        sa.Column("effect_entity", sa.String(length=128), nullable=False),
        sa.Column("effect_variable", sa.String(length=128), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), server_default="RELATIONSHIP", nullable=False),
        sa.Column("direction", sa.String(length=64), server_default="UNKNOWN", nullable=False),
        sa.Column("mechanism", sa.Text(), server_default="UNKNOWN", nullable=False),
        sa.Column("mechanism_status", sa.String(length=64), server_default="UNKNOWN", nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False),
        sa.Column("environment", sa.String(length=64), server_default="STAGING", nullable=False),
        sa.Column("software_version", sa.String(length=64), nullable=True),
        sa.Column("time_window", sa.JSON(), nullable=True),
        sa.Column("strength", sa.String(length=64), server_default="MODERATE", nullable=False),
        sa.Column("effect_size", sa.JSON(), nullable=True),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("experiment_refs", sa.JSON(), nullable=False),
        sa.Column("observation_refs", sa.JSON(), nullable=False),
        sa.Column("counterfactual_refs", sa.JSON(), nullable=False),
        sa.Column("verification_refs", sa.JSON(), nullable=False),
        sa.Column("contradiction_refs", sa.JSON(), nullable=False),
        sa.Column("falsification_criteria", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), server_default="CANDIDATE", nullable=False),
        sa.Column("model_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("previous_version_id", sa.String(length=64), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_crel_relation_id", "causal_relationships", ["relation_id"])
    op.create_index("ix_crel_tenant_id", "causal_relationships", ["tenant_id"])
    op.create_index("ix_crel_workspace_id", "causal_relationships", ["workspace_id"])
    op.create_index(
        "ix_crel_cause_effect_idx",
        "causal_relationships",
        ["cause_entity", "cause_variable", "effect_entity", "effect_variable"],
    )
    op.create_index("ix_crel_status_env_idx", "causal_relationships", ["status", "environment"])
    op.create_index("ix_crel_tenant_ws_idx", "causal_relationships", ["tenant_id", "workspace_id"])

    # 2. Causal Intervention Records
    op.create_table(
        "causal_intervention_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("intervention_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("target", sa.String(length=128), nullable=False),
        sa.Column("operator", sa.String(length=64), server_default="SYSTEM", nullable=False),
        sa.Column("experiment_id", sa.String(length=64), nullable=True),
        sa.Column("previous_state", sa.JSON(), nullable=False),
        sa.Column("new_state", sa.JSON(), nullable=False),
        sa.Column("environment", sa.String(length=64), server_default="STAGING", nullable=False),
        sa.Column("authorization", sa.JSON(), nullable=False),
        sa.Column("rollback_plan", sa.JSON(), nullable=False),
        sa.Column("observations", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), server_default="COMPLETED", nullable=False),
        sa.Column("is_controlled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cintrec_intervention_id", "causal_intervention_records", ["intervention_id"])
    op.create_index("ix_cintrec_tenant_id", "causal_intervention_records", ["tenant_id"])
    op.create_index("ix_cintrec_workspace_id", "causal_intervention_records", ["workspace_id"])
    op.create_index("ix_cintrec_target", "causal_intervention_records", ["target"])
    op.create_index("ix_cintrec_experiment_id", "causal_intervention_records", ["experiment_id"])
    op.create_index("ix_cintrec_target_env_idx", "causal_intervention_records", ["target", "environment"])
    op.create_index("ix_cintrec_status_idx", "causal_intervention_records", ["status"])

    # 3. Causal Audit Events
    op.create_table(
        "causal_audit_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("event_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("relation_id", sa.String(length=64), nullable=True),
        sa.Column("actor", sa.String(length=64), server_default="SYSTEM", nullable=False),
        sa.Column("source", sa.String(length=128), server_default="causal_engine", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_caud_event_id", "causal_audit_events", ["event_id"])
    op.create_index("ix_caud_tenant_id", "causal_audit_events", ["tenant_id"])
    op.create_index("ix_caud_workspace_id", "causal_audit_events", ["workspace_id"])
    op.create_index("ix_caud_event_type", "causal_audit_events", ["event_type"])
    op.create_index("ix_caud_relation_id", "causal_audit_events", ["relation_id"])
    op.create_index("ix_caud_type_ts_idx", "causal_audit_events", ["event_type", "timestamp"])

    # 4. Causal Drift Reports
    op.create_table(
        "causal_drift_reports",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("report_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("drift_type", sa.String(length=64), server_default="CAUSAL_DRIFT", nullable=False),
        sa.Column("relation_id", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=64), server_default="STAGING", nullable=False),
        sa.Column("software_version", sa.String(length=64), nullable=True),
        sa.Column("expected_behavior", sa.JSON(), nullable=False),
        sa.Column("observed_behavior", sa.JSON(), nullable=False),
        sa.Column("prediction_error", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("status", sa.String(length=64), server_default="DETECTED", nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cdrift_report_id", "causal_drift_reports", ["report_id"])
    op.create_index("ix_cdrift_tenant_id", "causal_drift_reports", ["tenant_id"])
    op.create_index("ix_cdrift_workspace_id", "causal_drift_reports", ["workspace_id"])
    op.create_index("ix_cdrift_relation_id", "causal_drift_reports", ["relation_id"])
    op.create_index("ix_cdrift_rel_type_idx", "causal_drift_reports", ["relation_id", "drift_type"])
    op.create_index("ix_cdrift_status_idx", "causal_drift_reports", ["status"])


def downgrade() -> None:
    op.drop_table("causal_drift_reports")
    op.drop_table("causal_audit_events")
    op.drop_table("causal_intervention_records")
    op.drop_table("causal_relationships")
