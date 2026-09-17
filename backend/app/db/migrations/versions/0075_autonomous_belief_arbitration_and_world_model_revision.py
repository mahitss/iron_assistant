"""Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine tables (Task 107).

Revision ID: 0075_autonomous_belief_arbitration_and_world_model_revision
Revises: 0074_autonomous_strategy_synthesis_and_operating_policy_engine
Create Date: 2026-09-18 02:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0075_autonomous_belief_arbitration_and_world_model_revision"
down_revision: str | None = "0074_autonomous_strategy_synthesis_and_operating_policy_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. belief_evidence_sources
    op.create_table(
        "belief_evidence_sources",
        sa.Column("source_id", sa.String(length=64), primary_key=True),
        sa.Column("source_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False, index=True),
        sa.Column("historical_reliability", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("provenance_domain", sa.String(length=128), server_default="system", nullable=False),
        sa.Column("is_verified_authority", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. belief_evidence_items
    op.create_table(
        "belief_evidence_items",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("freshness_ttl_seconds", sa.Integer(), server_default="300", nullable=False),
        sa.Column("integrity_verified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("derived_from_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("reliability_weight", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. belief_evidence_relationships
    op.create_table(
        "belief_evidence_relationships",
        sa.Column("relationship_id", sa.String(length=64), primary_key=True),
        sa.Column("source_evidence_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("target_evidence_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("relationship_type", sa.String(length=64), server_default="DERIVED_FROM", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. belief_evidence_assessments
    op.create_table(
        "belief_evidence_assessments",
        sa.Column("assessment_id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("outcome", sa.String(length=32), server_default="NEUTRAL", nullable=False, index=True),
        sa.Column("weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. belief_claims
    op.create_table(
        "belief_claims",
        sa.Column("claim_id", sa.String(length=64), primary_key=True),
        sa.Column("subject", sa.String(length=255), nullable=False, index=True),
        sa.Column("predicate", sa.String(length=255), nullable=False, index=True),
        sa.Column("object_value_json", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("uncertainty_type", sa.String(length=64), server_default="NONE", nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. belief_claim_versions
    op.create_table(
        "belief_claim_versions",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("predicate", sa.String(length=255), nullable=False),
        sa.Column("object_value_json", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uncertainty", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("uncertainty_type", sa.String(length=64), server_default="NONE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. belief_manifold
    op.create_table(
        "belief_manifold",
        sa.Column("belief_id", sa.String(length=64), primary_key=True),
        sa.Column("subject", sa.String(length=255), nullable=False, index=True),
        sa.Column("predicate", sa.String(length=255), nullable=False, index=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("current_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="CANDIDATE", nullable=False, index=True),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("uncertainty_type", sa.String(length=64), server_default="NONE", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_ttl_seconds", sa.Integer(), server_default="3600", nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False, index=True),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("contradiction_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. belief_manifold_versions
    op.create_table(
        "belief_manifold_versions",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("belief_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CANDIDATE", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("uncertainty_type", sa.String(length=64), server_default="NONE", nullable=False),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("contradiction_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("revision_reason", sa.String(length=64), server_default="NEW_EVIDENCE", nullable=False),
        sa.Column("revision_notes", sa.Text(), server_default="", nullable=False),
        sa.Column("version_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. belief_manifold_support
    op.create_table(
        "belief_manifold_support",
        sa.Column("support_id", sa.String(length=64), primary_key=True),
        sa.Column("belief_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("evidence_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("directness", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. belief_manifold_conflicts
    op.create_table(
        "belief_manifold_conflicts",
        sa.Column("conflict_id", sa.String(length=64), primary_key=True),
        sa.Column("belief_id_a", sa.String(length=64), nullable=False, index=True),
        sa.Column("belief_id_b", sa.String(length=64), nullable=True, index=True),
        sa.Column("claim_id_a", sa.String(length=64), nullable=False, index=True),
        sa.Column("claim_id_b", sa.String(length=64), nullable=True, index=True),
        sa.Column("conflict_type", sa.String(length=32), server_default="DIRECT", nullable=False, index=True),
        sa.Column("resolution", sa.String(length=32), server_default="CONTESTED", nullable=False, index=True),
        sa.Column("competing_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 11. belief_manifold_revisions
    op.create_table(
        "belief_manifold_revisions",
        sa.Column("revision_id", sa.String(length=64), primary_key=True),
        sa.Column("belief_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("prior_version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("new_version_number", sa.Integer(), server_default="2", nullable=False),
        sa.Column("prior_status", sa.String(length=32), server_default="CANDIDATE", nullable=False),
        sa.Column("new_status", sa.String(length=32), server_default="SUPPORTED", nullable=False),
        sa.Column("prior_confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("new_confidence", sa.Float(), server_default="0.6", nullable=False),
        sa.Column("reason", sa.String(length=64), server_default="NEW_EVIDENCE", nullable=False),
        sa.Column("evidence_id_trigger", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    # 12. belief_manifold_dependencies
    op.create_table(
        "belief_manifold_dependencies",
        sa.Column("dependency_id", sa.String(length=64), primary_key=True),
        sa.Column("parent_belief_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("child_belief_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("dependency_strength", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("is_hard_prerequisite", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 13. belief_manifold_snapshots
    op.create_table(
        "belief_manifold_snapshots",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("trigger_type", sa.String(length=64), server_default="MANUAL", nullable=False, index=True),
        sa.Column("reference_id", sa.String(length=128), nullable=True, index=True),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("beliefs_manifest", sa.JSON(), nullable=False),
        sa.Column("evidence_manifest", sa.JSON(), nullable=False),
        sa.Column("integrity_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 14. belief_manifold_validations
    op.create_table(
        "belief_manifold_validations",
        sa.Column("validation_id", sa.String(length=64), primary_key=True),
        sa.Column("belief_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("validator_type", sa.String(length=64), server_default="INDEPENDENT_EVALUATION", nullable=False),
        sa.Column("validator_ref", sa.String(length=128), server_default="", nullable=False),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("confidence_delta", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("evidence_produced_id", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 15. belief_manifold_corrections
    op.create_table(
        "belief_manifold_corrections",
        sa.Column("correction_id", sa.String(length=64), primary_key=True),
        sa.Column("belief_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source", sa.String(length=64), server_default="USER", nullable=False),
        sa.Column("correction_statement", sa.Text(), server_default="", nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. belief_manifold_expiries
    op.create_table(
        "belief_manifold_expiries",
        sa.Column("expiry_id", sa.String(length=64), primary_key=True),
        sa.Column("predicate_pattern", sa.String(length=255), server_default="*", nullable=False, index=True),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("ttl_seconds", sa.Integer(), server_default="3600", nullable=False),
        sa.Column("stale_action", sa.String(length=64), server_default="REVALIDATION_REQUIRED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 17. belief_manifold_events
    op.create_table(
        "belief_manifold_events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("belief_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("evidence_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("belief_manifold_events")
    op.drop_table("belief_manifold_expiries")
    op.drop_table("belief_manifold_corrections")
    op.drop_table("belief_manifold_validations")
    op.drop_table("belief_manifold_snapshots")
    op.drop_table("belief_manifold_dependencies")
    op.drop_table("belief_manifold_revisions")
    op.drop_table("belief_manifold_conflicts")
    op.drop_table("belief_manifold_support")
    op.drop_table("belief_manifold_versions")
    op.drop_table("belief_manifold")
    op.drop_table("belief_claim_versions")
    op.drop_table("belief_claims")
    op.drop_table("belief_evidence_assessments")
    op.drop_table("belief_evidence_relationships")
    op.drop_table("belief_evidence_items")
    op.drop_table("belief_evidence_sources")
