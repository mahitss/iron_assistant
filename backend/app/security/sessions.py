"""Security session lifecycle management and context validation."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.models import SecurityApprovalRequest, SecuritySession

logger = logging.getLogger("kairo.security.sessions")

DEFAULT_SESSION_TIMEOUT_MINUTES = 30


class SecuritySessionManager:
    """Manages active security sessions and cleanup of expired credentials."""

    def __init__(self, session_timeout_minutes: int = DEFAULT_SESSION_TIMEOUT_MINUTES) -> None:
        self.timeout_delta = timedelta(minutes=session_timeout_minutes)

    async def get_or_create_session(
        self,
        db_session: AsyncSession,
        user_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecuritySession:
        """Fetch an active session or create a new one."""
        now = datetime.now(UTC)

        if session_id:
            stmt = select(SecuritySession).where(
                SecuritySession.id == session_id,
                SecuritySession.user_id == user_id,
            )
            res = await db_session.execute(stmt)
            sec_sess = res.scalar_one_or_none()
            if sec_sess and sec_sess.is_active:
                # Check expiration
                if (now - sec_sess.last_activity_at) > self.timeout_delta:
                    sec_sess.is_active = False
                    await self._invalidate_session_approvals(db_session, sec_sess.id)
                    await db_session.commit()
                else:
                    sec_sess.last_activity_at = now
                    await db_session.commit()
                    return sec_sess

        # Create new active session
        new_sess = SecuritySession(
            user_id=user_id,
            created_at=now,
            last_activity_at=now,
            is_active=True,
            metadata_json=metadata or {},
        )
        db_session.add(new_sess)
        await db_session.commit()
        await db_session.refresh(new_sess)
        return new_sess

    async def terminate_session(self, db_session: AsyncSession, session_id: str, user_id: str) -> bool:
        """Deactivate a session and cancel all pending approvals."""
        stmt = select(SecuritySession).where(
            SecuritySession.id == session_id,
            SecuritySession.user_id == user_id,
        )
        res = await db_session.execute(stmt)
        sec_sess = res.scalar_one_or_none()
        if not sec_sess:
            return False

        sec_sess.is_active = False
        await self._invalidate_session_approvals(db_session, session_id)
        await db_session.commit()
        return True

    async def _invalidate_session_approvals(self, db_session: AsyncSession, session_id: str) -> None:
        """Cancel all pending approval requests attached to the expired session."""
        stmt = select(SecurityApprovalRequest).where(
            SecurityApprovalRequest.session_id == session_id,
            SecurityApprovalRequest.status == "pending",
        )
        res = await db_session.execute(stmt)
        pending = res.scalars().all()
        for apr in pending:
            apr.status = "cancelled"
            apr.decision_reason = "Session expired or terminated"
