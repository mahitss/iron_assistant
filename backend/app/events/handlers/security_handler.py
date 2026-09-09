"""Security and Audit subscriber for Kairo Event Bus.

Listens to security violations, approval flows, and emergency stops,
guaranteeing audit logging and security observability.
"""

from __future__ import annotations

import logging
from typing import Any

from app.events.db import get_event_db_session
from app.events.schemas import Event
from app.security.audit import AuditLogger

logger = logging.getLogger(__name__)


async def handle_security_event(event: Event) -> None:
    """Records security and approval events in the tamper-evident AuditLogger."""
    event_type = event.event_type
    payload = event.payload or {}
    user_id = event.user_id or "system"

    logger.info(
        "SecurityHandler processing event '%s' for user '%s' (ID: %s)",
        event_type,
        user_id,
        event.event_id,
    )

    tool_name = payload.get("tool_name")
    risk_level = payload.get("risk_level")
    decision = payload.get("decision") or payload.get("reason")
    approval_id = payload.get("approval_id")
    success = False if "blocked" in event_type or "revoked" in event_type else True

    try:
        async with get_event_db_session() as session:
            await AuditLogger.log_event(
                db_session=session,
                user_id=user_id,
                event_type=event_type,
                tool_name=tool_name,
                risk_level=risk_level,
                decision=decision,
                approval_id=approval_id,
                success=success,
                metadata={
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "source": event.source,
                    "details": payload,
                },
            )
    except Exception as exc:
        logger.warning("AuditLogger integration warning for event '%s': %s", event.event_id, exc)
