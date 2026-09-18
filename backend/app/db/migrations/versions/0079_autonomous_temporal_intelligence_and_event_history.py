"""Autonomous Temporal Intelligence, Event History, Change Reconstruction & "What Changed?" Engine tables (Task 111).

Revision ID: 0079_autonomous_temporal_intelligence_and_event_history
Revises: 0078_autonomous_cognitive_working_set_and_context_lifecycle
Create Date: 2026-09-18 06:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0079_autonomous_temporal_intelligence_and_event_history"
down_revision: str | None = "0078_autonomous_cognitive_working_set_and_context_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. temporal_events_t111
    op.create_table(
        "temporal_events_t111",
        sa.Column("temporal_event_id", sa.String(length=64), primary_key=True),
        sa.Column("canonical_event_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("event_version", sa.String(length=16), server_default="v1", nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, index=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("observed_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sequence_number", sa.Integer(), server_default="0", nullable=False, index=True),
        sa.Column("monotonic_timestamp", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("source_subsystem", sa.String(length=32), nullable=False, index=True),
        sa.Column("source_entity_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("actor_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("causation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("parent_event_id", sa.String(length=64), nullable=True),
        sa.Column("payload_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("payload_diff_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("is_untrusted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_late", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_out_of_order", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_duplicate", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("correction_state", sa.String(length=32), nullable=True),
        sa.Column("superseded_by", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_tevt_category_event_time", "temporal_events_t111", ["category", "event_time"])
    op.create_index("ix_tevt_entity_event_time", "temporal_events_t111", ["source_entity_id", "event_time"])
    op.create_index("ix_tevt_correlation_event_time", "temporal_events_t111", ["correlation_id", "event_time"])

    # 2. temporal_entities_t111
    op.create_table(
        "temporal_entities_t111",
        sa.Column("entity_id", sa.String(length=64), primary_key=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("scope", sa.String(length=64), server_default="DEFAULT", nullable=False, index=True),
        sa.Column("current_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("current_state", sa.String(length=64), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_transition_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state_attributes_json", sa.JSON(), nullable=False),
        sa.Column("provenance_source", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
    )
    op.create_index("ix_tent_type_scope", "temporal_entities_t111", ["entity_type", "scope"])

    # 3. temporal_state_transitions_t111
    op.create_table(
        "temporal_state_transitions_t111",
        sa.Column("transition_id", sa.String(length=64), primary_key=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("previous_state", sa.String(length=64), nullable=False),
        sa.Column("next_state", sa.String(length=64), nullable=False),
        sa.Column("trigger_event_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("actor", sa.String(length=64), nullable=True, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("expectation_status", sa.String(length=32), server_default="OBSERVED", nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("attribution", sa.String(length=32), server_default="UNATTRIBUTED", nullable=False),
        sa.Column("attributed_cause", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("scope", sa.String(length=64), server_default="DEFAULT", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_ttrans_entity_ts", "temporal_state_transitions_t111", ["entity_id", "timestamp"])
    op.create_index("ix_ttrans_attribution_ts", "temporal_state_transitions_t111", ["attribution", "timestamp"])

    # 4. temporal_changesets_t111
    op.create_table(
        "temporal_changesets_t111",
        sa.Column("changeset_id", sa.String(length=64), primary_key=True),
        sa.Column("from_reference", sa.String(length=128), nullable=False),
        sa.Column("to_reference", sa.String(length=128), nullable=False),
        sa.Column("from_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("to_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("added_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("removed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("modified_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("degraded_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recovered_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unattributed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. temporal_change_records_t111
    op.create_table(
        "temporal_change_records_t111",
        sa.Column("change_id", sa.String(length=64), primary_key=True),
        sa.Column("changeset_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("attribute_path", sa.String(length=128), nullable=False),
        sa.Column("previous_value_json", sa.JSON(), nullable=True),
        sa.Column("new_value_json", sa.JSON(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("attribution", sa.String(length=32), server_default="UNATTRIBUTED", nullable=False),
        sa.Column("attributed_action_id", sa.String(length=64), nullable=True),
        sa.Column("attributed_actor", sa.String(length=64), nullable=True),
        sa.Column("causal_evidence", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("impact_level", sa.String(length=16), server_default="LOW", nullable=False),
    )
    op.create_index("ix_tchg_entity_ts", "temporal_change_records_t111", ["entity_id", "timestamp"])

    # 6. temporal_anomalies_t111
    op.create_table(
        "temporal_anomalies_t111",
        sa.Column("anomaly_id", sa.String(length=64), primary_key=True),
        sa.Column("anomaly_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("event_ids_json", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("severity", sa.String(length=16), server_default="WARNING", nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("remediation_suggested", sa.Text(), nullable=True),
        sa.Column("is_adversarial_suspect", sa.Boolean(), server_default="0", nullable=False),
    )

    # 7. temporal_gaps_t111
    op.create_table(
        "temporal_gaps_t111",
        sa.Column("gap_id", sa.String(length=64), primary_key=True),
        sa.Column("subsystem", sa.String(length=32), nullable=False, index=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("gap_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gap_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("is_offline_period", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("confidence_impact", sa.Float(), server_default="0.5", nullable=False),
    )

    # 8. temporal_watermarks_t111
    op.create_table(
        "temporal_watermarks_t111",
        sa.Column("watermark_id", sa.String(length=64), primary_key=True),
        sa.Column("subsystem", sa.String(length=32), unique=True, nullable=False, index=True),
        sa.Column("source_watermark", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_watermark", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_watermark", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconciliation_watermark", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. temporal_checkpoints_t111
    op.create_table(
        "temporal_checkpoints_t111",
        sa.Column("checkpoint_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, index=True),
        sa.Column("checkpoint_type", sa.String(length=32), server_default="MANUAL", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("active_entity_states_json", sa.JSON(), nullable=False),
        sa.Column("state_snapshot_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("creator", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("temporal_checkpoints_t111")
    op.drop_table("temporal_watermarks_t111")
    op.drop_table("temporal_gaps_t111")
    op.drop_table("temporal_anomalies_t111")
    op.drop_table("temporal_change_records_t111")
    op.drop_table("temporal_changesets_t111")
    op.drop_table("temporal_state_transitions_t111")
    op.drop_table("temporal_entities_t111")
    op.drop_table("temporal_events_t111")
