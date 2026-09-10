"""Situational awareness and event correlation engine tables (Task 60).

Revision ID: 0040_situational_awareness_and_event_correlation
Revises: 0039_resource_and_capability_orchestration
Create Date: 2026-09-10 23:25:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0040_situational_awareness_and_event_correlation"
down_revision: str | None = "0039_resource_and_capability_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Situations Table
    op.create_table(
        "situations",
        sa.Column("situation_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DETECTED"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="development"),
        sa.Column("affected_resources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("affected_services", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("affected_plans", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("affected_goals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("current_state", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("expected_state", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("timeline", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("risk_assessment", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("next_steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("flapping_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situations_situation_id", "situations", ["situation_id"])
    op.create_index("ix_situations_status", "situations", ["status"])
    op.create_index("ix_situations_severity", "situations", ["severity"])
    op.create_index("ix_situations_environment", "situations", ["environment"])

    # 2. Normalized Events Table
    op.create_table(
        "situation_events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("situation_id", sa.String(length=64), sa.ForeignKey("situations.situation_id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_trust", sa.String(length=64), nullable=False, server_default="TRUSTED_SYSTEM"),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="development"),
        sa.Column("resource", sa.String(length=128), nullable=True),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="INFO"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("causation_id", sa.String(length=64), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situation_events_event_id", "situation_events", ["event_id"])
    op.create_index("ix_situation_events_situation_id", "situation_events", ["situation_id"])
    op.create_index("ix_situation_events_event_type", "situation_events", ["event_type"])
    op.create_index("ix_situation_events_source", "situation_events", ["source"])
    op.create_index("ix_situation_events_resource", "situation_events", ["resource"])
    op.create_index("ix_situation_events_correlation_id", "situation_events", ["correlation_id"])
    op.create_index("ix_situation_events_occurred_at", "situation_events", ["occurred_at"])

    # 3. Signal Baselines Table
    op.create_table(
        "signal_baselines",
        sa.Column("baseline_id", sa.String(length=64), primary_key=True),
        sa.Column("signal_name", sa.String(length=128), nullable=False),
        sa.Column("resource", sa.String(length=128), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="development"),
        sa.Column("mean_val", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("std_dev", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("min_val", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_val", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_quarantined", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("last_calibrated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signal_baselines_baseline_id", "signal_baselines", ["baseline_id"])
    op.create_index("ix_signal_baselines_signal_name", "signal_baselines", ["signal_name"])
    op.create_index("ix_signal_baselines_resource", "signal_baselines", ["resource"])

    # 4. Causal Hypotheses Table
    op.create_table(
        "situation_hypotheses",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("situation_id", sa.String(length=64), sa.ForeignKey("situations.situation_id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_cause", sa.String(length=256), nullable=False),
        sa.Column("confidence_level", sa.String(length=32), nullable=False, server_default="LIKELY"),
        sa.Column("evidence_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommended_diagnostics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situation_hypotheses_hypothesis_id", "situation_hypotheses", ["hypothesis_id"])
    op.create_index("ix_situation_hypotheses_situation_id", "situation_hypotheses", ["situation_id"])

    # 5. Situation Audit Log Table
    op.create_table(
        "situation_audit_log",
        sa.Column("audit_id", sa.String(length=64), primary_key=True),
        sa.Column("situation_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_situation_audit_log_audit_id", "situation_audit_log", ["audit_id"])
    op.create_index("ix_situation_audit_log_situation_id", "situation_audit_log", ["situation_id"])


def downgrade() -> None:
    op.drop_table("situation_audit_log")
    op.drop_table("situation_hypotheses")
    op.drop_table("signal_baselines")
    op.drop_table("situation_events")
    op.drop_table("situations")
