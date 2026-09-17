"""Autonomous world-state reconstruction, state estimation, reality synchronization and drift reconciliation engine tables (Task 98).

Revision ID: 0066_autonomous_world_state_reconciliation
Revises: 0065_autonomous_knowledge_graph_reasoning
Create Date: 2026-09-17 21:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0066_autonomous_world_state_reconciliation"
down_revision: str | None = "0065_autonomous_knowledge_graph_reasoning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. world_state_snapshots
    op.create_table(
        "world_state_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("scope", sa.String(length=32), server_default="SYSTEM", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("certainty", sa.String(length=32), server_default="KNOWN", nullable=False),
        sa.Column("freshness", sa.String(length=32), server_default="FRESH", nullable=False),
        sa.Column("drift_status", sa.String(length=32), server_default="NORMAL", nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("entities_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_world_state_snapshots_scope", "world_state_snapshots", ["scope"])
    op.create_index("ix_world_state_snapshots_created", "world_state_snapshots", ["created_at"])
    op.create_index("ix_world_state_snapshots_scope_created", "world_state_snapshots", ["scope", "created_at"])

    # 2. state_observations
    op.create_table(
        "state_observations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), server_default="", nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("observed_value_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("certainty", sa.String(length=32), server_default="KNOWN", nullable=False),
        sa.Column("sensitivity", sa.String(length=32), server_default="INTERNAL", nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="SYSTEM", nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_state_obs_source", "state_observations", ["source"])
    op.create_index("ix_state_obs_entity", "state_observations", ["entity_id"])
    op.create_index("ix_state_obs_scope", "state_observations", ["scope"])
    op.create_index("ix_state_obs_observed_at", "state_observations", ["observed_at"])
    op.create_index("ix_state_obs_entity_time", "state_observations", ["entity_id", "observed_at"])

    # 3. state_drift_records
    op.create_table(
        "state_drift_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="SYSTEM", nullable=False),
        sa.Column("drift_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("classification", sa.String(length=64), server_default="ACTIONABLE_DRIFT", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DETECTED", nullable=False),
        sa.Column("expected_value_json", sa.JSON(), nullable=False),
        sa.Column("actual_value_json", sa.JSON(), nullable=False),
        sa.Column("deviation_magnitude", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("causal_status", sa.String(length=64), server_default="UNKNOWN", nullable=False),
        sa.Column("attributed_source_type", sa.String(length=64), nullable=True),
        sa.Column("attributed_source_id", sa.String(length=128), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_state_drift_entity", "state_drift_records", ["entity_id"])
    op.create_index("ix_state_drift_scope", "state_drift_records", ["scope"])
    op.create_index("ix_state_drift_type", "state_drift_records", ["drift_type"])
    op.create_index("ix_state_drift_severity", "state_drift_records", ["severity"])
    op.create_index("ix_state_drift_status", "state_drift_records", ["status"])
    op.create_index("ix_state_drift_detected", "state_drift_records", ["detected_at"])
    op.create_index("ix_state_drift_entity_severity", "state_drift_records", ["entity_id", "severity"])

    # 4. state_conflict_records
    op.create_table(
        "state_conflict_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("attribute_name", sa.String(length=64), nullable=False),
        sa.Column("resolution_state", sa.String(length=32), server_default="UNRESOLVED", nullable=False),
        sa.Column("resolved_value_json", sa.JSON(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_state_conflict_entity", "state_conflict_records", ["entity_id"])
    op.create_index("ix_state_conflict_state", "state_conflict_records", ["resolution_state"])
    op.create_index("ix_state_conflict_detected", "state_conflict_records", ["detected_at"])

    # 5. revalidation_candidates
    op.create_table(
        "revalidation_candidates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("drift_id", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=32), server_default="NORMAL", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reval_cand_entity", "revalidation_candidates", ["entity_id"])
    op.create_index("ix_reval_cand_type", "revalidation_candidates", ["target_type"])
    op.create_index("ix_reval_cand_drift", "revalidation_candidates", ["drift_id"])
    op.create_index("ix_reval_cand_priority", "revalidation_candidates", ["priority"])
    op.create_index("ix_reval_cand_status", "revalidation_candidates", ["status"])
    op.create_index("ix_reval_cand_created", "revalidation_candidates", ["created_at"])


def downgrade() -> None:
    op.drop_table("revalidation_candidates")
    op.drop_table("state_conflict_records")
    op.drop_table("state_drift_records")
    op.drop_table("state_observations")
    op.drop_table("world_state_snapshots")
