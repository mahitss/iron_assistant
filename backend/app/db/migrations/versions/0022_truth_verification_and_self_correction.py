"""Migration for Kairo Truth, Verification, and Self-Correction Engine (Task 42).

Revision ID: 0022_truth_verification_and_self_correction
Revises: 0021_cognitive_planning_and_reasoning
Create Date: 2026-09-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_truth_verification_and_self_correction"
down_revision: str | None = "0021_cognitive_planning_and_reasoning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. verification_claims table
    op.create_table(
        "verification_claims",
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("predicate", sa.String(length=128), nullable=False),
        sa.Column("object_ref", sa.String(length=256), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("claim_type", sa.String(length=32), nullable=False, server_default="FACT"),
        sa.Column("truth_status", sa.String(length=32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("claim_id"),
    )
    op.create_index("ix_verification_claims_user_id", "verification_claims", ["user_id"])
    op.create_index("ix_verification_claims_project_id", "verification_claims", ["project_id"])
    op.create_index("ix_verification_claims_claim_type", "verification_claims", ["claim_type"])
    op.create_index("ix_verification_claims_truth_status", "verification_claims", ["truth_status"])

    # 2. verification_evidence table
    op.create_table(
        "verification_evidence",
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=256), nullable=False),
        sa.Column("observation", sa.JSON(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("freshness_seconds", sa.Float(), nullable=False, server_default="300.0"),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("evidence_id"),
    )
    op.create_index("ix_verification_evidence_user_id", "verification_evidence", ["user_id"])
    op.create_index("ix_verification_evidence_project_id", "verification_evidence", ["project_id"])
    op.create_index("ix_verification_evidence_source_type", "verification_evidence", ["source_type"])

    # 3. verification_contracts table
    op.create_table(
        "verification_contracts",
        sa.Column("contract_id", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=256), nullable=False),
        sa.Column("expected_state", sa.JSON(), nullable=False),
        sa.Column("verification_steps", sa.JSON(), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=False, server_default="30.0"),
        sa.Column("required_evidence", sa.JSON(), nullable=False),
        sa.Column("failure_behavior", sa.String(length=32), nullable=False, server_default="BLOCK"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("contract_id"),
    )

    # 4. verification_results table
    op.create_table(
        "verification_results",
        sa.Column("result_id", sa.String(length=64), nullable=False),
        sa.Column("contract_id", sa.String(length=64), nullable=False),
        sa.Column("claim_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="UNKNOWN"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("discrepancies", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("verifier", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["verification_contracts.contract_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["verification_claims.claim_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("result_id"),
    )
    op.create_index("ix_verification_results_contract_id", "verification_results", ["contract_id"])
    op.create_index("ix_verification_results_claim_id", "verification_results", ["claim_id"])
    op.create_index("ix_verification_results_status", "verification_results", ["status"])

    # 5. verification_corrections table
    op.create_table(
        "verification_corrections",
        sa.Column("correction_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("original_claim_id", sa.String(length=64), nullable=False),
        sa.Column("corrected_claim_id", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["original_claim_id"], ["verification_claims.claim_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["corrected_claim_id"], ["verification_claims.claim_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("correction_id"),
    )
    op.create_index("ix_verification_corrections_user_id", "verification_corrections", ["user_id"])

    # 6. verification_invariants table
    op.create_table(
        "verification_invariants",
        sa.Column("invariant_id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="HIGH"),
        sa.Column("predicate_spec", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("invariant_id"),
    )
    op.create_index("ix_verification_invariants_domain", "verification_invariants", ["domain"])


def downgrade() -> None:
    op.drop_table("verification_invariants")
    op.drop_table("verification_corrections")
    op.drop_table("verification_results")
    op.drop_table("verification_contracts")
    op.drop_table("verification_evidence")
    op.drop_table("verification_claims")
