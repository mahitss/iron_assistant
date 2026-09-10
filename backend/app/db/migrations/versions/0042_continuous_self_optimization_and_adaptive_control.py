"""Continuous self-optimization and adaptive control engine tables (Task 62).

Revision ID: 0042_continuous_self_optimization_and_adaptive_control
Revises: 0041_incident_response_and_recovery_autonomy
Create Date: 2026-09-11 00:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0042_continuous_self_optimization_and_adaptive_control"
down_revision: str | None = "0041_incident_response_and_recovery_autonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Optimization Objectives Table
    op.create_table(
        "optimization_objectives",
        sa.Column("objective_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False, server_default="MINIMIZE"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_objectives_objective_id", "optimization_objectives", ["objective_id"])
    op.create_index("ix_optimization_objectives_metric_name", "optimization_objectives", ["metric_name"])

    # 2. Optimization Metrics Table
    op.create_table(
        "optimization_metrics",
        sa.Column("measurement_id", sa.String(length=64), primary_key=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False, server_default="telemetry"),
        sa.Column("scope", sa.String(length=128), nullable=False, server_default="global"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_metrics_measurement_id", "optimization_metrics", ["measurement_id"])
    op.create_index("ix_optimization_metrics_metric_name", "optimization_metrics", ["metric_name"])
    op.create_index("ix_optimization_metrics_timestamp", "optimization_metrics", ["timestamp"])

    # 3. Optimization Baselines Table
    op.create_table(
        "optimization_baselines",
        sa.Column("baseline_id", sa.String(length=64), primary_key=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("std_dev", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="production"),
        sa.Column("is_quarantined", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_baselines_baseline_id", "optimization_baselines", ["baseline_id"])
    op.create_index("ix_optimization_baselines_metric_name", "optimization_baselines", ["metric_name"])

    # 4. Optimization Experiments Table
    op.create_table(
        "optimization_experiments",
        sa.Column("experiment_id", sa.String(length=64), primary_key=True),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("target_metrics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("control_parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("variants", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("safety_gates", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("stop_conditions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_experiments_experiment_id", "optimization_experiments", ["experiment_id"])
    op.create_index("ix_optimization_experiments_status", "optimization_experiments", ["status"])

    # 5. Optimization Change Sets Table
    op.create_table(
        "optimization_change_sets",
        sa.Column("change_set_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("target_parameter", sa.String(length=128), nullable=False),
        sa.Column("before_state", sa.Float(), nullable=False),
        sa.Column("after_state", sa.Float(), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("risk", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("approver", sa.String(length=128), nullable=True),
        sa.Column("rollback_strategy", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_change_sets_change_set_id", "optimization_change_sets", ["change_set_id"])
    op.create_index("ix_optimization_change_sets_status", "optimization_change_sets", ["status"])

    # 6. Optimization Canaries Table
    op.create_table(
        "optimization_canaries",
        sa.Column("canary_id", sa.String(length=64), primary_key=True),
        sa.Column("change_set_id", sa.String(length=64), nullable=False),
        sa.Column("rollout_state", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("traffic_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("blast_radius_scope", sa.String(length=64), nullable=False, server_default="canary_partition"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("failure_threshold_reached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_canaries_canary_id", "optimization_canaries", ["canary_id"])
    op.create_index("ix_optimization_canaries_change_set_id", "optimization_canaries", ["change_set_id"])
    op.create_index("ix_optimization_canaries_rollout_state", "optimization_canaries", ["rollout_state"])

    # 7. Optimization Drift Records Table
    op.create_table(
        "optimization_drift_records",
        sa.Column("drift_id", sa.String(length=64), primary_key=True),
        sa.Column("drift_type", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("divergence_score", sa.Float(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_drift_records_drift_id", "optimization_drift_records", ["drift_id"])
    op.create_index("ix_optimization_drift_records_drift_type", "optimization_drift_records", ["drift_type"])

    # 8. Optimization Audit Trail Table
    op.create_table(
        "optimization_audit_log",
        sa.Column("entry_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("recommendation_id", sa.String(length=64), nullable=True),
        sa.Column("change_set_id", sa.String(length=64), nullable=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_audit_log_sequence_number", "optimization_audit_log", ["sequence_number"])
    op.create_index("ix_optimization_audit_log_event_type", "optimization_audit_log", ["event_type"])


def downgrade() -> None:
    op.drop_table("optimization_audit_log")
    op.drop_table("optimization_drift_records")
    op.drop_table("optimization_canaries")
    op.drop_table("optimization_change_sets")
    op.drop_table("optimization_experiments")
    op.drop_table("optimization_baselines")
    op.drop_table("optimization_metrics")
    op.drop_table("optimization_objectives")
