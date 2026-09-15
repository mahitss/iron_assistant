"""Autonomous capability lifecycle, versioning, compatibility and safe evolution engine tables (Task 91).

Revision ID: 0059_autonomous_capability_lifecycle_and_evolution_engine
Revises: 0058_autonomous_governance_constitutional_reasoning_and_authority_engine
Create Date: 2026-09-15 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0059_autonomous_capability_lifecycle_and_evolution_engine"
down_revision: str | None = "0058_autonomous_governance_constitutional_reasoning_and_authority_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Capabilities
    op.create_table(
        "capabilities",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("capability_type", sa.String(length=32), server_default="TOOL", nullable=False),
        sa.Column("owner_source", sa.String(length=128), server_default="core.kairo", nullable=False),
        sa.Column("version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("contract_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("implementation_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("composite_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), server_default="DISCOVERED", nullable=False),
        sa.Column("health_state", sa.String(length=32), server_default="UNKNOWN", nullable=False),
        sa.Column("security_classification", sa.String(length=32), server_default="INTERNAL", nullable=False),
        sa.Column("parameters_schema", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("output_schema", sa.JSON(), nullable=True),
        sa.Column("dependencies_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("resource_profile_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("reliability_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("active_version_id", sa.String(length=64), nullable=True),
        sa.Column("canary_version_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_capabilities_capability_id", "capabilities", ["capability_id"], unique=True)
    op.create_index("ix_capabilities_lifecycle_state", "capabilities", ["lifecycle_state"])
    op.create_index("ix_capabilities_type_state", "capabilities", ["capability_type", "lifecycle_state"])

    # 2. Capability Versions
    op.create_table(
        "capability_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("version_str", sa.String(length=32), nullable=False),
        sa.Column("major", sa.Integer(), server_default="1", nullable=False),
        sa.Column("minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("patch", sa.Integer(), server_default="0", nullable=False),
        sa.Column("contract_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("implementation_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("dependency_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_capability_versions_cap_ver", "capability_versions", ["capability_id", "version_str"], unique=True)

    # 3. Capability Lifecycle Events
    op.create_table(
        "capability_lifecycle_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), server_default="", nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=False),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("actor", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("safety_metadata", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_capability_lifecycle_events_cap", "capability_lifecycle_events", ["capability_id"])
    op.create_index("ix_capability_lifecycle_events_corr", "capability_lifecycle_events", ["correlation_id"])

    # 4. Capability Rollouts
    op.create_table(
        "capability_rollouts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("target_version", sa.String(length=32), nullable=False),
        sa.Column("current_percent", sa.Float(), server_default="5.0", nullable=False),
        sa.Column("workloads_routed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("errors_encountered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("state", sa.String(length=32), server_default="INACTIVE", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_capability_rollouts_cap", "capability_rollouts", ["capability_id"])


def downgrade() -> None:
    op.drop_table("capability_rollouts")
    op.drop_table("capability_lifecycle_events")
    op.drop_table("capability_versions")
    op.drop_table("capabilities")
