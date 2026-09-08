"""Append-only audit logging and query service for security events."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.models import SecurityAuditEvent
from app.security.redaction import ArgumentSanitizer

logger = logging.getLogger("kairo.security.audit")


class AuditLogger:
    """Records immutable audit trail events and retrieves user-scoped activity history."""

    @classmethod
    async def log_event(
        cls,
        db_session: AsyncSession | None,
        user_id: str,
        event_type: str,
        tool_name: str | None = None,
        session_id: str | None = None,
        risk_level: str | None = None,
        decision: str | None = None,
        approval_id: str | None = None,
        success: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityAuditEvent:
        """Create and persist an append-only audit event with redacted metadata."""
        now = datetime.now(UTC)
        sanitized_meta = ArgumentSanitizer.sanitize(metadata or {})

        event = SecurityAuditEvent(
            user_id=user_id,
            session_id=session_id,
            timestamp=now,
            event_type=event_type,
            tool_name=tool_name,
            risk_level=risk_level,
            decision=decision,
            approval_id=approval_id,
            success=success,
            metadata_json=sanitized_meta,
        )

        logger.info(
            "AUDIT [%s] user=%s tool=%s risk=%s decision=%s success=%s",
            event_type,
            user_id,
            tool_name,
            risk_level,
            decision,
            success,
        )

        if db_session is not None:
            db_session.add(event)
            await db_session.commit()
            await db_session.refresh(event)

        return event

    @classmethod
    async def query_events(
        cls,
        db_session: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
        tool_name: str | None = None,
    ) -> tuple[list[SecurityAuditEvent], int]:
        """Fetch audit events strictly scoped to user_id, with optional filtering and pagination."""
        base_query = select(SecurityAuditEvent).where(SecurityAuditEvent.user_id == user_id)
        count_query = select(func.count(SecurityAuditEvent.id)).where(SecurityAuditEvent.user_id == user_id)

        if event_type:
            base_query = base_query.where(SecurityAuditEvent.event_type == event_type)
            count_query = count_query.where(SecurityAuditEvent.event_type == event_type)

        if tool_name:
            base_query = base_query.where(SecurityAuditEvent.tool_name == tool_name)
            count_query = count_query.where(SecurityAuditEvent.tool_name == tool_name)

        total_res = await db_session.execute(count_query)
        total = total_res.scalar_one()

        items_query = base_query.order_by(desc(SecurityAuditEvent.timestamp)).offset(offset).limit(limit)
        items_res = await db_session.execute(items_query)
        items = list(items_res.scalars().all())

        return items, total
