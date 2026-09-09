"""Migration for Predictive Intelligence, Forecasting, Early Warning, and Risk Anticipation (Task 47).

Revision ID: 0027_predictive_intelligence
Revises: 0026_perception_awareness
Create Date: 2026-09-10 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_predictive_intelligence"
down_revision: str | None = "0026_perception_awareness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. predictions
    op.create_table(
        "predictions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("event", sa.String(length=128), nullable=False),
        sa.Column("predicted_state", sa.JSON(), nullable=False),
        sa.Column("prediction_window", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_reference", sa.String(length=128), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("actual_outcome", sa.JSON(), nullable=True),
        sa.Column("action_influenced", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_subject", "predictions", ["subject"])
    op.create_index("ix_predictions_status", "predictions", ["status"])
    op.create_index("ix_predictions_expires_at", "predictions", ["expires_at"])

    # 2. forecasts
    op.create_table(
        "forecasts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=256), nullable=False),
        sa.Column("scenarios", sa.JSON(), nullable=False),
        sa.Column("likelihood", sa.Float(), nullable=False),
        sa.Column("timeframe", sa.String(length=64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("uncertainty", sa.Float(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("previous_version_id", sa.String(length=64), nullable=True),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecasts_target", "forecasts", ["target"])

    # 3. early_warnings
    op.create_table(
        "early_warnings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=256), nullable=False),
        sa.Column("signal", sa.String(length=128), nullable=False),
        sa.Column("predicted_event", sa.String(length=256), nullable=False),
        sa.Column("timeframe", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_early_warnings_target", "early_warnings", ["target"])
    op.create_index("ix_early_warnings_status", "early_warnings", ["status"])
    op.create_index("ix_early_warnings_severity", "early_warnings", ["severity"])

    # 4. predicted_risks
    op.create_table(
        "predicted_risks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("event", sa.String(length=256), nullable=False),
        sa.Column("likelihood", sa.Float(), nullable=False),
        sa.Column("impact", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("timeframe", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("mitigations", sa.JSON(), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predicted_risks_subject", "predicted_risks", ["subject"])
    op.create_index("ix_predicted_risks_risk_score", "predicted_risks", ["risk_score"])

    # 5. prediction_triggers
    op.create_table(
        "prediction_triggers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("condition_expr", sa.String(length=256), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("action_class", sa.String(length=32), nullable=False),
        sa.Column("required_evidence", sa.JSON(), nullable=False),
        sa.Column("authorization_scope", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_triggers_status", "prediction_triggers", ["status"])

    # 6. prediction_calibrations
    op.create_table(
        "prediction_calibrations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("model_reference", sa.String(length=128), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("brier_score", sa.Float(), nullable=False),
        sa.Column("log_loss", sa.Float(), nullable=False),
        sa.Column("calibration_error", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pred_calib_model", "prediction_calibrations", ["model_reference"])


def downgrade() -> None:
    op.drop_table("prediction_calibrations")
    op.drop_table("prediction_triggers")
    op.drop_table("predicted_risks")
    op.drop_table("early_warnings")
    op.drop_table("forecasts")
    op.drop_table("predictions")
