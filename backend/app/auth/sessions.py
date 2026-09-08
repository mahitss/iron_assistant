"""Session store and security session lifecycle management."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.auth.schemas import AuthSession, UserRole
from app.config.settings import get_settings

logger = logging.getLogger("kairo.auth.sessions")


class SessionStore:
    """Manages active security sessions, idle timeouts, and revocation."""

    def __init__(self, default_ttl_seconds: int = 86400, idle_timeout_seconds: int = 1800) -> None:
        self.default_ttl = default_ttl_seconds
        self.idle_timeout = idle_timeout_seconds
        self._in_memory_sessions: dict[str, AuthSession] = {}
        self._token_to_session: dict[str, str] = {}

    def create_session(
        self,
        user_id: str,
        token: str,
        role: UserRole = UserRole.USER,
        metadata: dict[str, Any] | None = None,
    ) -> AuthSession:
        """Create and register a new security session."""
        now = datetime.now(timezone.utc)
        session_id = f"sess_{now.strftime('%Y%m%d%H%M%S')}_{token[:8]}"
        expires_at = now + timedelta(seconds=self.default_ttl)

        session = AuthSession(
            session_id=session_id,
            user_id=user_id,
            role=role,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            is_revoked=False,
            metadata=metadata or {},
        )

        self._in_memory_sessions[session_id] = session
        self._token_to_session[token] = session_id
        logger.info("Created security session '%s' for user '%s'.", session_id, user_id)
        return session

    def get_session_by_token(self, token: str) -> AuthSession | None:
        """Retrieve session by bearer token, validating expiration and idle timeout."""
        session_id = self._token_to_session.get(token)
        if not session_id:
            return None

        session = self._in_memory_sessions.get(session_id)
        if not session:
            return None

        if session.is_revoked:
            logger.warning("Attempt to access revoked session '%s'.", session_id)
            return None

        now = datetime.now(timezone.utc)
        # Check absolute expiration
        if now > session.expires_at:
            logger.info("Session '%s' expired (absolute TTL reached).", session_id)
            self.revoke_session(session_id, reason="Expired")
            return None

        # Check idle timeout
        idle_duration = (now - session.last_activity).total_seconds()
        if idle_duration > self.idle_timeout:
            logger.info("Session '%s' timed out (idle for %ds).", session_id, idle_duration)
            self.revoke_session(session_id, reason="Idle timeout")
            return None

        # Update last activity
        session.last_activity = now
        return session

    def get_session(self, session_id: str) -> AuthSession | None:
        """Retrieve session by ID."""
        session = self._in_memory_sessions.get(session_id)
        if not session or session.is_revoked:
            return None
        return session

    def revoke_session(self, session_id: str, reason: str = "User logout") -> bool:
        """Revoke active session and trigger SecurityCenter cleanup."""
        session = self._in_memory_sessions.get(session_id)
        if not session:
            return False

        session.is_revoked = True
        logger.info("Revoked session '%s' for user '%s' (Reason: %s).", session_id, session.user_id, reason)

        # Invalidate associated token mappings
        tokens_to_remove = [t for t, sid in self._token_to_session.items() if sid == session_id]
        for t in tokens_to_remove:
            self._token_to_session.pop(t, None)

        # Integrate with SecurityCenter: cancel pending approvals for this session/user
        try:
            from app.security.center import get_security_center

            sec_center = get_security_center()
            if sec_center and sec_center.approvals:
                # Reject/expire pending approvals for user
                pending = sec_center.approvals.list_pending(user_id=session.user_id)
                for apprv in pending:
                    sec_center.approvals.resolve(
                        approval_id=apprv.id,
                        decision="rejected",
                        user_id=session.user_id,
                        denial_reason=f"Security session revoked: {reason}",
                    )
                logger.info(
                    "Invalidated %d pending approvals for revoked user '%s'.", len(pending), session.user_id
                )
        except Exception as exc:
            logger.warning("Could not sync session revocation with SecurityCenter: %s", exc)

        return True

    def clear(self) -> None:
        """Clear all active sessions (used in test fixtures)."""
        self._in_memory_sessions.clear()
        self._token_to_session.clear()


_SESSION_STORE: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Return the global session store instance."""
    global _SESSION_STORE
    if _SESSION_STORE is None:
        cfg = get_settings()
        _SESSION_STORE = SessionStore(
            default_ttl_seconds=getattr(cfg, "KAIRO_AUTH_SESSION_TTL_SECONDS", 86400),
            idle_timeout_seconds=getattr(cfg, "KAIRO_AUTH_IDLE_TIMEOUT_SECONDS", 1800),
        )
    return _SESSION_STORE
