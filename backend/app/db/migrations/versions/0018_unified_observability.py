"""Migration for Kairo Unified Observability, Distributed Tracing, Incidents, and Diagnostics (Task 38).

Revision ID: 0018_unified_observability
Revises: 0017_resilience_and_recovery
Create Date: 2026-09-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_unified_observability"
down_revision: str | None = "0017_resilience_and_recovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. observability_traces table
    op.create_table(
        "observability_traces",
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("root_operation", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RUNNING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("trace_id"),
    )
    op.create_index("ix_observability_traces_user_id", "observability_traces", ["user_id"])
    op.create_index("ix_observability_traces_task_id", "observability_traces", ["task_id"])
    op.create_index("ix_observability_traces_project_id", "observability_traces", ["project_id"])
    op.create_index("ix_observability_traces_status", "observability_traces", ["status"])
    op.create_index("ix_observability_traces_started_at", "observability_traces", ["started_at"])

    # 2. observability_spans table
    op.create_table(
        "observability_spans",
        sa.Column("span_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("parent_span_id", sa.String(length=64), nullable=True),
        sa.Column("operation", sa.String(length=128), nullable=False),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RUNNING"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("attributes_json", sa.JSON(), nullable=True),
        sa.Column("events_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("span_id"),
    )
    op.create_index("ix_observability_spans_trace_id", "observability_spans", ["trace_id"])
    op.create_index("ix_observability_spans_parent_span_id", "observability_spans", ["parent_span_id"])
    op.create_index("ix_observability_spans_component", "observability_spans", ["component"])
    op.create_index("ix_observability_spans_status", "observability_spans", ["status"])
    op.create_index("ix_observability_spans_started_at", "observability_spans", ["started_at"])

    # 3. observability_incidents table
    op.create_table(
        "observability_incidents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("affected_components_json", sa.JSON(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("root_cause_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observability_incidents_status", "observability_incidents", ["status"])
    op.create_index("ix_observability_incidents_severity", "observability_incidents", ["severity"])
    op.create_index("ix_observability_incidents_created_at", "observability_incidents", ["created_at"])


def downgrade() -> None:
    op.drop_table("observability_incidents")
    op.drop_table("observability_spans")
    op.drop_table("observability_traces")
