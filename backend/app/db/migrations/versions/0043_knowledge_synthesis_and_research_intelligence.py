"""Knowledge synthesis and research intelligence engine tables (Task 63).

Revision ID: 0043_knowledge_synthesis_and_research_intelligence
Revises: 0042_continuous_self_optimization_and_adaptive_control
Create Date: 2026-09-11 01:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0043_knowledge_synthesis_and_research_intelligence"
down_revision: str | None = "0042_continuous_self_optimization_and_adaptive_control"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Research Sessions Table
    op.create_table(
        "research_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("objective", sa.String(length=255), nullable=False, server_default="Knowledge Synthesis"),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="global"),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="STANDARD"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="COMPLETED"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_sessions_session_id", "research_sessions", ["session_id"])
    op.create_index("ix_research_sessions_tenant_id", "research_sessions", ["tenant_id"])

    # 2. Research Sources Table
    op.create_table(
        "research_sources",
        sa.Column("source_id", sa.String(length=64), primary_key=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=False, server_default="Unknown"),
        sa.Column("author", sa.String(length=255), nullable=False, server_default="Unknown"),
        sa.Column("url_or_reference", sa.Text(), nullable=False),
        sa.Column("authority_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_retracted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_sources_source_id", "research_sources", ["source_id"])

    # 3. Research Documents Table
    op.create_table(
        "research_documents",
        sa.Column("document_id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False, server_default="markdown"),
        sa.Column("content_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("raw_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_documents_document_id", "research_documents", ["document_id"])
    op.create_index("ix_research_documents_source_id", "research_documents", ["source_id"])

    # 4. Research Claims Table
    op.create_table(
        "research_claims",
        sa.Column("claim_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("predicate", sa.String(length=255), nullable=False),
        sa.Column("object", sa.Text(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=64), nullable=False, server_default="REPORTED"),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default="MODERATE"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_claims_claim_id", "research_claims", ["claim_id"])
    op.create_index("ix_research_claims_session_id", "research_claims", ["session_id"])
    op.create_index("ix_research_claims_source_id", "research_claims", ["source_id"])

    # 5. Research Evidence Table
    op.create_table(
        "research_evidence",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("excerpt_reference", sa.Text(), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False, server_default="PRIMARY_DOCUMENT"),
        sa.Column("strength", sa.String(length=32), nullable=False, server_default="MODERATE"),
        sa.Column("directness", sa.String(length=32), nullable=False, server_default="DIRECT"),
        sa.Column("independence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_evidence_evidence_id", "research_evidence", ["evidence_id"])
    op.create_index("ix_research_evidence_claim_id", "research_evidence", ["claim_id"])

    # 6. Research Conflicts Table
    op.create_table(
        "research_conflicts",
        sa.Column("conflict_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("claim_a_id", sa.String(length=64), nullable=False),
        sa.Column("claim_b_id", sa.String(length=64), nullable=False),
        sa.Column("conflict_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="UNRESOLVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_conflicts_conflict_id", "research_conflicts", ["conflict_id"])
    op.create_index("ix_research_conflicts_session_id", "research_conflicts", ["session_id"])

    # 7. Research Gaps Table
    op.create_table(
        "research_gaps",
        sa.Column("gap_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=32), nullable=False, server_default="HIGH"),
        sa.Column("impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_gaps_gap_id", "research_gaps", ["gap_id"])
    op.create_index("ix_research_gaps_session_id", "research_gaps", ["session_id"])

    # 8. Research Audits Table
    op.create_table(
        "research_audits",
        sa.Column("sequence_number", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("claim_id", sa.String(length=64), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_audits_session_id", "research_audits", ["session_id"])


def downgrade() -> None:
    op.drop_table("research_audits")
    op.drop_table("research_gaps")
    op.drop_table("research_conflicts")
    op.drop_table("research_evidence")
    op.drop_table("research_claims")
    op.drop_table("research_documents")
    op.drop_table("research_sources")
    op.drop_table("research_sessions")
