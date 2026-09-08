"""Idempotency key generation for scheduled and manual workflow runs."""

import uuid
from datetime import datetime


def generate_scheduled_idempotency_key(workflow_id: str, scheduled_time: datetime) -> str:
    """Generate a deterministic idempotency key for scheduled workflow triggers.

    Ensures that identical schedule intervals cannot trigger duplicate side effects.
    """
    ts = int(scheduled_time.timestamp())
    return f"sched_{workflow_id}_{ts}"


def generate_manual_idempotency_key(workflow_id: str, client_token: str | None = None) -> str:
    """Generate a unique or client-supplied idempotency key for manual runs."""
    token = client_token.strip() if client_token and client_token.strip() else str(uuid.uuid4())
    return f"manual_{workflow_id}_{token}"
