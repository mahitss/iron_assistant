"""Resource and capability orchestration engine tables (Task 59).

Revision ID: 0039_resource_and_capability_orchestration
Revises: 0038_strategic_planning_and_execution
Create Date: 2026-09-10 23:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0039_resource_and_capability_orchestration"
down_revision: str | None = "0038_strategic_planning_and_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Capabilities Catalog
    op.create_table(
        "capabilities",
        sa.Column("capability_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("cost_estimate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("supported_environments", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("required_permissions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("required_resources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("input_schema", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_schema", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("verification_method", sa.String(length=128), nullable=False, server_default="ASSERTION"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="AVAILABLE"),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_capabilities_capability_id", "capabilities", ["capability_id"])
    op.create_index("ix_capabilities_name", "capabilities", ["name"])
    op.create_index("ix_capabilities_provider", "capabilities", ["provider"])
    op.create_index("ix_capabilities_status", "capabilities", ["status"])

    # 2. Orchestration Resources
    op.create_table(
        "orchestration_resources",
        sa.Column("resource_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False, server_default="SYSTEM"),
        sa.Column("total_capacity", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("available_capacity", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("allocated_capacity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("reserved_capacity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="units"),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="development"),
        sa.Column("health", sa.String(length=32), nullable=False, server_default="HEALTHY"),
        sa.Column("cost_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("constraints", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("ownership", sa.String(length=128), nullable=False, server_default="SYSTEM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="AVAILABLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orchestration_resources_resource_id", "orchestration_resources", ["resource_id"])
    op.create_index("ix_orchestration_resources_name", "orchestration_resources", ["name"])
    op.create_index("ix_orchestration_resources_resource_type", "orchestration_resources", ["resource_type"])
    op.create_index("ix_orchestration_resources_status", "orchestration_resources", ["status"])

    # 3. Resource Reservations
    op.create_table(
        "resource_reservations",
        sa.Column("reservation_id", sa.String(length=64), primary_key=True),
        sa.Column("resource_id", sa.String(length=64), sa.ForeignKey("orchestration_resources.resource_id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("purpose", sa.String(length=256), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False, server_default="GLOBAL"),
        sa.Column("amount", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("authorization_signature", sa.String(length=256), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resource_reservations_reservation_id", "resource_reservations", ["reservation_id"])
    op.create_index("ix_resource_reservations_resource_id", "resource_reservations", ["resource_id"])

    # 4. Orchestration Plans
    op.create_table(
        "orchestration_plans",
        sa.Column("orchestration_id", sa.String(length=64), primary_key=True),
        sa.Column("strategic_plan_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("task_graph", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("execution_waves", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("health", sa.String(length=32), nullable=False, server_default="ON_TRACK"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orchestration_plans_orchestration_id", "orchestration_plans", ["orchestration_id"])
    op.create_index("ix_orchestration_plans_strategic_plan_id", "orchestration_plans", ["strategic_plan_id"])
    op.create_index("ix_orchestration_plans_status", "orchestration_plans", ["status"])

    # 5. Task Assignments
    op.create_table(
        "task_assignments",
        sa.Column("assignment_id", sa.String(length=64), primary_key=True),
        sa.Column("orchestration_id", sa.String(length=64), sa.ForeignKey("orchestration_plans.orchestration_id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False, server_default="TOOL"),
        sa.Column("capability_id", sa.String(length=64), nullable=False),
        sa.Column("allocated_resources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("required_permissions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ASSIGNED"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("fallback_provider", sa.String(length=128), nullable=True),
        sa.Column("verification_criteria", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_assignments_assignment_id", "task_assignments", ["assignment_id"])
    op.create_index("ix_task_assignments_orchestration_id", "task_assignments", ["orchestration_id"])
    op.create_index("ix_task_assignments_task_id", "task_assignments", ["task_id"])

    # 6. Orchestration Revisions
    op.create_table(
        "orchestration_revisions",
        sa.Column("revision_id", sa.String(length=64), primary_key=True),
        sa.Column("parent_orchestration_id", sa.String(length=64), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("diff_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orchestration_revisions_revision_id", "orchestration_revisions", ["revision_id"])
    op.create_index("ix_orchestration_revisions_parent_orchestration_id", "orchestration_revisions", ["parent_orchestration_id"])

    # 7. Orchestration Outcomes
    op.create_table(
        "orchestration_outcomes",
        sa.Column("outcome_id", sa.String(length=64), primary_key=True),
        sa.Column("orchestration_id", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("actual_duration", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("variance_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("lessons_learned", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orchestration_outcomes_outcome_id", "orchestration_outcomes", ["outcome_id"])
    op.create_index("ix_orchestration_outcomes_orchestration_id", "orchestration_outcomes", ["orchestration_id"])


def downgrade() -> None:
    op.drop_table("orchestration_outcomes")
    op.drop_table("orchestration_revisions")
    op.drop_table("task_assignments")
    op.drop_table("orchestration_plans")
    op.drop_table("resource_reservations")
    op.drop_table("orchestration_resources")
    op.drop_table("capabilities")
