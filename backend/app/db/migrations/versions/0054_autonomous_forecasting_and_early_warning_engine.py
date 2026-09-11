"""Autonomous forecasting and early-warning engine tables (Task 74).

Revision ID: 0054_autonomous_forecasting_and_early_warning_engine
Revises: 0053_autonomous_causal_discovery_and_world_model_engine
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0054_autonomous_forecasting_and_early_warning_engine"
down_revision: str | None = "0053_autonomous_causal_discovery_and_world_model_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Forecast Versions
    op.create_table(
        "forecast_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("forecast_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("previous_version_id", sa.String(length=64), nullable=True),
        sa.Column("change_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("changed_inputs", sa.JSON(), nullable=False),
        sa.Column("changed_model", sa.String(length=128), nullable=True),
        sa.Column("changed_assumptions", sa.JSON(), nullable=False),
        sa.Column("likelihood_delta", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("point_estimate_delta", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fcv_forecast_id", "forecast_versions", ["forecast_id"])

    # 2. Forecast Evaluations
    op.create_table(
        "forecast_evaluations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("forecast_id", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=256), nullable=False),
        sa.Column("realized_outcome", sa.JSON(), nullable=False),
        sa.Column("realized_value", sa.Float(), nullable=True),
        sa.Column("error_metrics", sa.JSON(), nullable=False),
        sa.Column("baseline_comparison", sa.JSON(), nullable=False),
        sa.Column("action_influenced", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fce_forecast_id", "forecast_evaluations", ["forecast_id"])
    op.create_index("ix_fce_target", "forecast_evaluations", ["target"])

    # 3. Forecast Leading Indicators
    op.create_table(
        "forecast_leading_indicators",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("indicator_id", sa.String(length=128), nullable=False),
        sa.Column("target_metric", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("direction", sa.String(length=32), server_default="increasing", nullable=False),
        sa.Column("lead_time_seconds", sa.Integer(), server_default="3600", nullable=False),
        sa.Column("historical_reliability", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("current_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("baseline_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("deviation", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fli_indicator_id", "forecast_leading_indicators", ["indicator_id"], unique=True)
    op.create_index("ix_fli_target_metric", "forecast_leading_indicators", ["target_metric"])

    # 4. Forecast Drifts
    op.create_table(
        "forecast_drifts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("target", sa.String(length=256), nullable=False),
        sa.Column("drift_type", sa.String(length=64), nullable=False),
        sa.Column("p_value_or_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("threshold", sa.Float(), server_default="0.05", nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("action_taken", sa.String(length=128), server_default="LOGGED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_drf_target", "forecast_drifts", ["target"])
    op.create_index("ix_drf_drift_type", "forecast_drifts", ["drift_type"])

    # 5. Forecast Warning Records
    op.create_table(
        "forecast_warning_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("warning_id", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("target", sa.String(length=256), nullable=False),
        sa.Column("signal", sa.String(length=128), nullable=False),
        sa.Column("predicted_event", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="INFO", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("hysteresis_state", sa.JSON(), nullable=False),
        sa.Column("resolution", sa.String(length=64), nullable=True),
        sa.Column("lead_time_seconds", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fwr_warning_id", "forecast_warning_records", ["warning_id"], unique=True)
    op.create_index("ix_fwr_fingerprint", "forecast_warning_records", ["fingerprint"])
    op.create_index("ix_fwr_target", "forecast_warning_records", ["target"])
    op.create_index("ix_fwr_status", "forecast_warning_records", ["status"])


def downgrade() -> None:
    op.drop_table("forecast_warning_records")
    op.drop_table("forecast_drifts")
    op.drop_table("forecast_leading_indicators")
    op.drop_table("forecast_evaluations")
    op.drop_table("forecast_versions")
