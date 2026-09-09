"""Migration for Kairo Resilience, Recovery, Fault-Tolerant Runtime, Checkpointing, and Retries (Task 37).

Revision ID: 0017_resilience_and_recovery
Revises: 0016_governance_and_policy_engine
Create Date: 2026-09-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_resilience_and_recovery"
down_revision: str | None = "0016_governance_and_policy_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. resilience_idempotency table
    op.create_table(
        "resilience_idempotency",
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="STARTED"),
        sa.Column("result_reference", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )
    op.create_index("ix_resilience_idempotency_operation", "resilience_idempotency", ["operation"])
    op.create_index("ix_resilience_idempotency_expires_at", "resilience_idempotency", ["expires_at"])

    # 2. resilience_leases table
    op.create_table(
        "resilience_leases",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index("ix_resilience_leases_worker_id", "resilience_leases", ["worker_id"])
    op.create_index("ix_resilience_leases_expires_at", "resilience_leases", ["expires_at"])

    # 3. resilience_checkpoints table
    op.create_table(
        "resilience_checkpoints",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resilience_checkpoints_task_id", "resilience_checkpoints", ["task_id"])
    op.create_index("ix_resilience_checkpoints_task_created", "resilience_checkpoints", ["task_id", "created_at"])

    # 4. resilience_quarantine table
    op.create_table(
        "resilience_quarantine",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quarantined_by", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUARANTINED"),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index("ix_resilience_quarantine_status", "resilience_quarantine", ["status"])

    # 5. resilience_circuit_states table
    op.create_table(
        "resilience_circuit_states",
        sa.Column("circuit_id", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="CLOSED"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("circuit_id"),
    )


def downgrade() -> None:
    op.drop_table("resilience_circuit_states")
    op.drop_table("resilience_quarantine")
    op.drop_table("resilience_checkpoints")
    op.drop_table("resilience_leases")
    op.drop_table("resilience_idempotency")
