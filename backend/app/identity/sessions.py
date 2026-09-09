"""Session manager governing lifecycle, timeouts, limits, and revocation (Spec 4, 6-9, 56, 120, 121)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.identity.models import IdentitySessionModel
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.schemas import ClientType, IdentityErrorCode, SessionCreateRequest, SessionResponse, SessionStatus
from app.security.exceptions import SecurityPolicyViolationError, TenantIsolationError

logger = logging.getLogger("kairo.identity.sessions")


class SessionManager:
    """Manages relational interactive sessions, idle timeouts, session limits, and revocation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.default_ttl = getattr(self.settings, "KAIRO_IDENTITY_SESSION_TTL_SECONDS", 86400)
        self.idle_timeout = getattr(self.settings, "KAIRO_IDENTITY_SESSION_IDLE_TIMEOUT_SECONDS", 3600)
        self.max_sessions = getattr(self.settings, "KAIRO_IDENTITY_MAX_SESSIONS_PER_USER", 10)

    async def create_session(
        self,
        user_id: str,
        client_type: ClientType,
        device_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> SessionResponse:
        """Create a new authenticated interactive session enforcing session limits (Spec 4, 6, 121)."""
        now = datetime.now(UTC)
        ttl = ttl_seconds or self.default_ttl
        expires_at = now + timedelta(seconds=ttl)

        # Enforce max sessions per user: revoke oldest active session if limit exceeded
        active_stmt = (
            select(IdentitySessionModel)
            .where(
                IdentitySessionModel.user_id == user_id,
                IdentitySessionModel.status == SessionStatus.ACTIVE.value,
            )
            .order_by(IdentitySessionModel.last_activity_at.asc())
        )
        active_res = await self.db.execute(active_stmt)
        active_sessions = list(active_res.scalars().all())

        if len(active_sessions) >= self.max_sessions:
            oldest = active_sessions[0]
            logger.info("Max active sessions (%d) reached for user '%s'. Revoking oldest session '%s'.", self.max_sessions, user_id, oldest.session_id)
            oldest.status = SessionStatus.REVOKED.value
            oldest.revoked_at = now

        session = IdentitySessionModel(
            user_id=user_id,
            client_type=client_type.value if hasattr(client_type, "value") else str(client_type),
            device_id=device_id,
            status=SessionStatus.ACTIVE.value,
            created_at=now,
            last_activity_at=now,
            expires_at=expires_at,
            metadata_json=metadata or {},
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info("Created identity session '%s' (user=%s, client=%s, device=%s)", session.session_id, user_id, client_type, device_id)

        # Publish session.created event to EventBus
        try:
            from app.events import event_bus
            from app.events.schemas import EventSource
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="session.created",
                    source="identity",
                    payload={
                        "session_id": session.session_id,
                        "client_type": session.client_type,
                        "device_id": session.device_id,
                    },
                    user_id=user_id,
                )
            )
        except Exception as eb_err:
            logger.debug("EventBus session.created publication skipped: %s", eb_err)

        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            client_type=ClientType(session.client_type),
            device_id=session.device_id,
            status=SessionStatus(session.status),
            created_at=session.created_at,
            last_activity_at=session.last_activity_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            metadata=session.metadata_json or {},
        )

    async def get_session(self, session_id: str, touch: bool = True) -> IdentitySessionModel:
        """Fetch session and validate activity, expiration, and idle boundaries."""
        session = await self.db.get(IdentitySessionModel, session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        # Invariant check: active status, expiration, and idle timeout
        IdentityPolicyEnforcer.enforce_session_active(session, idle_timeout_seconds=self.idle_timeout)

        if touch:
            session.last_activity_at = datetime.now(UTC)
            await self.db.commit()

        return session

    async def revoke_session(self, session_id: str, user_id: str, reason: str = "User initiated revocation") -> SessionResponse:
        """Revoke an active session with tenant validation (Spec 8)."""
        session = await self.db.get(IdentitySessionModel, session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        if session.user_id != user_id:
            raise TenantIsolationError(f"Cannot revoke session '{session_id}' belonging to another user.")

        now = datetime.now(UTC)
        session.status = SessionStatus.REVOKED.value
        session.revoked_at = now
        await self.db.commit()
        await self.db.refresh(session)

        logger.info("Revoked identity session '%s' for user '%s' (Reason: %s)", session_id, user_id, reason)

        # Invalidate in-memory auth store if mapped
        try:
            from app.auth.sessions import get_session_store
            store = get_session_store()
            store.revoke_session(session_id, reason=reason)
        except Exception:
            pass

        # Publish session.revoked event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="session.revoked",
                    source="identity",
                    payload={
                        "session_id": session.session_id,
                        "reason": reason,
                    },
                    user_id=user_id,
                )
            )
        except Exception as eb_err:
            logger.debug("EventBus session.revoked publication skipped: %s", eb_err)

        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            client_type=ClientType(session.client_type),
            device_id=session.device_id,
            status=SessionStatus(session.status),
            created_at=session.created_at,
            last_activity_at=session.last_activity_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            metadata=session.metadata_json or {},
        )

    async def revoke_all_sessions(
        self, user_id: str, except_session_id: str | None = None, reason: str = "Global sign out everywhere"
    ) -> int:
        """Sign out everywhere: revokes all active sessions for user (Spec 9, 78)."""
        now = datetime.now(UTC)
        stmt = (
            select(IdentitySessionModel)
            .where(
                IdentitySessionModel.user_id == user_id,
                IdentitySessionModel.status == SessionStatus.ACTIVE.value,
            )
        )
        if except_session_id:
            stmt = stmt.where(IdentitySessionModel.session_id != except_session_id)

        res = await self.db.execute(stmt)
        sessions_to_revoke = list(res.scalars().all())

        for sess in sessions_to_revoke:
            sess.status = SessionStatus.REVOKED.value
            sess.revoked_at = now

        await self.db.commit()
        count = len(sessions_to_revoke)
        logger.info("Global sign-out: Revoked %d active sessions for user '%s'.", count, user_id)

        # Also revoke all in in-memory auth store
        try:
            from app.auth.sessions import get_session_store
            store = get_session_store()
            for s in sessions_to_revoke:
                store.revoke_session(s.session_id, reason=reason)
        except Exception:
            pass

        # Publish event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="session.revoked",
                    source="identity",
                    payload={"revoked_all": True, "count": count, "reason": reason},
                    user_id=user_id,
                )
            )
        except Exception:
            pass

        return count

    async def list_user_sessions(self, user_id: str, include_revoked: bool = False) -> list[SessionResponse]:
        """Fetch all sessions belonging to the authenticated user."""
        stmt = select(IdentitySessionModel).where(IdentitySessionModel.user_id == user_id)
        if not include_revoked:
            stmt = stmt.where(IdentitySessionModel.status == SessionStatus.ACTIVE.value)
        stmt = stmt.order_by(IdentitySessionModel.last_activity_at.desc())

        res = await self.db.execute(stmt)
        sessions = res.scalars().all()

        return [
            SessionResponse(
                session_id=s.session_id,
                user_id=s.user_id,
                client_type=ClientType(s.client_type),
                device_id=s.device_id,
                status=SessionStatus(s.status),
                created_at=s.created_at,
                last_activity_at=s.last_activity_at,
                expires_at=s.expires_at,
                revoked_at=s.revoked_at,
                metadata=s.metadata_json or {},
            )
            for s in sessions
        ]
