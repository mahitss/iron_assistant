"""Autonomous governance, constitutional reasoning, policy intelligence and authority engine tables (Task 78).

Revision ID: 0058_autonomous_governance_constitutional_reasoning_and_authority_engine
Revises: 0057_autonomous_resource_economy_and_cognitive_budget_engine
Create Date: 2026-09-13 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0058_autonomous_governance_constitutional_reasoning_and_authority_engine"
down_revision: str | None = "0057_autonomous_resource_economy_and_cognitive_budget_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Constitutions
    op.create_table(
        "constitutions",
        sa.Column("constitution_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_constitutions_is_active", "constitutions", ["is_active"])

    # 2. Constitutional Principles
    op.create_table(
        "constitutional_principles",
        sa.Column("principle_id", sa.String(length=64), primary_key=True),
        sa.Column("constitution_id", sa.String(length=64), sa.ForeignKey("constitutions.constitution_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("strictness", sa.String(length=32), server_default="MANDATORY", nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_constitutional_principles_constitution_id", "constitutional_principles", ["constitution_id"])
    op.create_index("ix_constitutional_principles_name", "constitutional_principles", ["name"])

    # 3. Authority Grants
    op.create_table(
        "authority_grants",
        sa.Column("grant_id", sa.String(length=64), primary_key=True),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=32), server_default="AGENT", nullable=False),
        sa.Column("authority_level", sa.String(length=32), server_default="LIMITED", nullable=False),
        sa.Column("allowed_scopes", sa.JSON(), nullable=False),
        sa.Column("allowed_actions", sa.JSON(), nullable=False),
        sa.Column("denied_actions", sa.JSON(), nullable=False),
        sa.Column("max_risk_level", sa.String(length=32), server_default="R2_MODERATE", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_authority_grants_subject_id", "authority_grants", ["subject_id"])
    op.create_index("ix_authority_grants_authority_level", "authority_grants", ["authority_level"])
    op.create_index("ix_authority_grants_is_active", "authority_grants", ["is_active"])

    # 4. Governance Decisions
    op.create_table(
        "governance_decisions",
        sa.Column("decision_id", sa.String(length=64), primary_key=True),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("caller_id", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), server_default="EXECUTABLE", nullable=False),
        sa.Column("authority_check_passed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("policy_tier_applied", sa.String(length=32), nullable=True),
        sa.Column("constitutional_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("requires_human", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_governance_decisions_review_id", "governance_decisions", ["review_id"])
    op.create_index("ix_governance_decisions_tenant_id", "governance_decisions", ["tenant_id"])
    op.create_index("ix_governance_decisions_decision", "governance_decisions", ["decision"])
    op.create_index("ix_governance_decisions_state", "governance_decisions", ["state"])

    # 5. Authority Escalation Incidents
    op.create_table(
        "authority_escalation_incidents",
        sa.Column("incident_id", sa.String(length=64), primary_key=True),
        sa.Column("caller_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("bypass_technique", sa.String(length=128), nullable=True),
        sa.Column("severity", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("flagged_actions", sa.JSON(), nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_authority_escalation_incidents_caller_id", "authority_escalation_incidents", ["caller_id"])


def downgrade() -> None:
    op.drop_table("authority_escalation_incidents")
    op.drop_table("governance_decisions")
    op.drop_table("authority_grants")
    op.drop_table("constitutional_principles")
    op.drop_table("constitutions")
