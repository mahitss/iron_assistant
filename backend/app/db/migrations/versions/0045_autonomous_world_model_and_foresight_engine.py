"""Autonomous world model and long-horizon foresight engine tables (Task 65).

Revision ID: 0045_autonomous_world_model_and_foresight_engine
Revises: 0044_collective_intelligence_and_swarm_reasoning
Create Date: 2026-09-11 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0045_autonomous_world_model_and_foresight_engine"
down_revision: str | None = "0044_collective_intelligence_and_swarm_reasoning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Foresight Entities
    op.create_table(
        "foresight_entities",
        sa.Column("entity_id", sa.String(length=64), primary_key=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("attributes_json", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="UNKNOWN"),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="SYSTEM"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("uncertainty", sa.String(length=32), nullable=False, server_default="LIKELY"),
        sa.Column("authority", sa.String(length=32), nullable=False, server_default="OBSERVED"),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_foresight_ent_tenant_type", "foresight_entities", ["tenant_id", "type"])
    op.create_index("ix_foresight_ent_state", "foresight_entities", ["state"])

    # 2. Foresight Relationships
    op.create_table(
        "foresight_relationships",
        sa.Column("rel_id", sa.String(length=128), primary_key=True),
        sa.Column("source_entity_id", sa.String(length=64), nullable=False),
        sa.Column("target_entity_id", sa.String(length=64), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False),
        sa.Column("causal_strength", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="SYSTEM"),
        sa.Column("is_critical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_foresight_rel_src_tgt", "foresight_relationships", ["source_entity_id", "target_entity_id"])
    op.create_index("ix_foresight_rel_type", "foresight_relationships", ["relationship_type"])

    # 3. Foresight State History
    op.create_table(
        "foresight_state_history",
        sa.Column("record_id", sa.String(length=64), primary_key=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("authority", sa.String(length=32), nullable=False, server_default="OBSERVED"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_foresight_hist_entity_obs", "foresight_state_history", ["entity_id", "observed_at"])

    # 4. Foresight Forecasts
    op.create_table(
        "foresight_forecasts",
        sa.Column("forecast_id", sa.String(length=64), primary_key=True),
        sa.Column("topic", sa.String(length=256), nullable=False),
        sa.Column("horizon", sa.String(length=32), nullable=False),
        sa.Column("intervals_json", sa.JSON(), nullable=False),
        sa.Column("prediction_summary", sa.Text(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("competing_hypotheses_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False, server_default="ensemble"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("actual_outcome", sa.Text(), nullable=True),
        sa.Column("calibration_score", sa.Float(), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_foresight_fct_tenant", "foresight_forecasts", ["tenant_id"])
    op.create_index("ix_foresight_fct_horizon", "foresight_forecasts", ["horizon"])

    # 5. Foresight Scenarios
    op.create_table(
        "foresight_scenarios",
        sa.Column("scenario_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="BASELINE"),
        sa.Column("horizon", sa.String(length=32), nullable=False),
        sa.Column("initial_state_summary", sa.Text(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("interventions_json", sa.JSON(), nullable=False),
        sa.Column("expected_changes_json", sa.JSON(), nullable=False),
        sa.Column("risks_json", sa.JSON(), nullable=False),
        sa.Column("opportunities_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_robust", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sensitivity_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_foresight_scn_tenant", "foresight_scenarios", ["tenant_id"])
    op.create_index("ix_foresight_scn_type", "foresight_scenarios", ["type"])

    # 6. Foresight Risks
    op.create_table(
        "foresight_risks",
        sa.Column("risk_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("impact", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("time_horizon", sa.String(length=32), nullable=False, server_default="MID_FUTURE_1M"),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("mitigations_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 7. Foresight Opportunities
    op.create_table(
        "foresight_opportunities",
        sa.Column("opportunity_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("potential_value", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("time_horizon", sa.String(length=32), nullable=False, server_default="MID_FUTURE_1M"),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("risks_json", sa.JSON(), nullable=False),
        sa.Column("optionality_score", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="IDENTIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 8. Foresight Early Warnings
    op.create_table(
        "foresight_early_warnings",
        sa.Column("signal_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("trend", sa.String(length=32), nullable=False, server_default="ACCELERATING"),
        sa.Column("affected_entities_json", sa.JSON(), nullable=False),
        sa.Column("trigger_condition", sa.String(length=256), nullable=False),
        sa.Column("leading_indicators_json", sa.JSON(), nullable=False),
        sa.Column("blast_radius_json", sa.JSON(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 9. Foresight Monitoring Plans
    op.create_table(
        "foresight_monitoring_plans",
        sa.Column("plan_id", sa.String(length=64), primary_key=True),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False, server_default="risk"),
        sa.Column("signals_json", sa.JSON(), nullable=False),
        sa.Column("thresholds_json", sa.JSON(), nullable=False),
        sa.Column("frequency_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 10. Foresight Audit Records
    op.create_table(
        "foresight_audit_records",
        sa.Column("record_id", sa.String(length=64), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_foresight_audit_hash", "foresight_audit_records", ["record_hash"])


def downgrade() -> None:
    op.drop_table("foresight_audit_records")
    op.drop_table("foresight_monitoring_plans")
    op.drop_table("foresight_early_warnings")
    op.drop_table("foresight_opportunities")
    op.drop_table("foresight_risks")
    op.drop_table("foresight_scenarios")
    op.drop_table("foresight_forecasts")
    op.drop_table("foresight_state_history")
    op.drop_table("foresight_relationships")
    op.drop_table("foresight_entities")
