"""Migration for Kairo Local Companion and Device Management.

Revision ID: 0007_device_runtime
Revises: 0006_personal_context
Create Date: 2026-09-09 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_device_runtime"
down_revision: str | None = "0006_personal_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=False),
        sa.Column("os_name", sa.String(length=32), nullable=False),
        sa.Column("os_version", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("companion_version", sa.String(length=32), nullable=False, server_default="1.1.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("credentials_hash", sa.String(length=128), nullable=True),
        sa.Column("computer_control_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("camera_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("filesystem_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allowed_paths", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"], unique=False)
    op.create_index("ix_devices_status", "devices", ["status"], unique=False)
    op.create_index("ix_devices_user_id_status", "devices", ["user_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_devices_user_id_status", table_name="devices")
    op.drop_index("ix_devices_status", table_name="devices")
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_table("devices")
