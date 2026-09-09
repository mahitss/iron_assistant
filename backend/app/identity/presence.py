"""Application-level presence tracking and rate-limited heartbeats (Spec 21-25, 55, 118, 119)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.devices.models import DeviceModel
from app.identity.models import IdentityPresenceModel, IdentitySessionModel
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.schemas import PresenceResponse, PresenceState, PresenceUpdateRequest, SessionStatus, UserOnlineStatus
from app.security.exceptions import SecurityPolicyViolationError, TenantIsolationError

logger = logging.getLogger("kairo.identity.presence")


class PresenceTracker:
    """Tracks application-level interface presence without invasive physical surveillance."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.timeout_seconds = getattr(self.settings, "KAIRO_IDENTITY_PRESENCE_TIMEOUT_SECONDS", 90)
        # Minimum interval between heartbeats per session to prevent traffic spam (Spec 119)
        self.min_heartbeat_interval_seconds = 5

    async def update_presence(self, user_id: str, request: PresenceUpdateRequest) -> PresenceResponse:
        """Process rate-limited application heartbeat (Spec 24, 119)."""
        now = datetime.now(UTC)

        # 1. Validate session
        session = await self.db.get(IdentitySessionModel, request.session_id)
        if not session:
            raise KeyError(f"Session '{request.session_id}' not found.")

        if session.user_id != user_id:
            raise TenantIsolationError("Session belongs to another user.")

        if session.status == SessionStatus.REVOKED.value:
            raise SecurityPolicyViolationError("Cannot update presence for a REVOKED session.")

        # 2. Find existing presence record for (user_id, session_id)
        stmt = select(IdentityPresenceModel).where(
            IdentityPresenceModel.user_id == user_id,
            IdentityPresenceModel.session_id == request.session_id,
        )
        res = await self.db.execute(stmt)
        record = res.scalars().first()

        if record:
            # Enforce heartbeat rate limiting
            last_seen = record.last_seen_at if record.last_seen_at.tzinfo is not None else record.last_seen_at.replace(tzinfo=UTC)
            delta = (now - last_seen).total_seconds()
            if delta < self.min_heartbeat_interval_seconds:
                # Silently return current without DB write spam
                return PresenceResponse(
                    id=record.id,
                    user_id=record.user_id,
                    session_id=record.session_id,
                    device_id=record.device_id,
                    interface=record.interface,
                    state=PresenceState(record.state),
                    last_seen_at=record.last_seen_at,
                )

            record.interface = request.interface
            record.device_id = request.device_id or record.device_id
            record.state = request.state.value if hasattr(request.state, "value") else str(request.state)
            record.last_seen_at = now
        else:
            record = IdentityPresenceModel(
                user_id=user_id,
                session_id=request.session_id,
                device_id=request.device_id,
                interface=request.interface,
                state=request.state.value if hasattr(request.state, "value") else str(request.state),
                last_seen_at=now,
            )
            self.db.add(record)

        # Touch session activity
        session.last_activity_at = now

        # If device bound, touch device last_seen_at
        if request.device_id:
            device = await self.db.get(DeviceModel, request.device_id)
            if device and device.user_id == user_id:
                device.last_seen_at = now

        await self.db.commit()
        await self.db.refresh(record)

        return PresenceResponse(
            id=record.id,
            user_id=record.user_id,
            session_id=record.session_id,
            device_id=record.device_id,
            interface=record.interface,
            state=PresenceState(record.state),
            last_seen_at=record.last_seen_at,
        )

    async def get_presence(self, user_id: str) -> list[PresenceResponse]:
        """Fetch real-time application presence applying disconnect timeouts (Spec 25)."""
        now = datetime.now(UTC)
        stmt = select(IdentityPresenceModel).where(IdentityPresenceModel.user_id == user_id)
        res = await self.db.execute(stmt)
        records = list(res.scalars().all())

        results = []
        dirty = False
        for rec in records:
            last_seen = rec.last_seen_at if rec.last_seen_at.tzinfo is not None else rec.last_seen_at.replace(tzinfo=UTC)
            delta = (now - last_seen).total_seconds()
            if delta > self.timeout_seconds and rec.state != PresenceState.DISCONNECTED.value:
                # Heartbeat stopped: mark DISCONNECTED (Spec 25)
                rec.state = PresenceState.DISCONNECTED.value
                dirty = True

            results.append(
                PresenceResponse(
                    id=rec.id,
                    user_id=rec.user_id,
                    session_id=rec.session_id,
                    device_id=rec.device_id,
                    interface=rec.interface,
                    state=PresenceState(rec.state),
                    last_seen_at=rec.last_seen_at,
                )
            )

        if dirty:
            await self.db.commit()

        return results

    async def get_user_online_status(self, user_id: str) -> UserOnlineStatus:
        """Get aggregated user online status. Never claims physical online (Spec 23)."""
        presences = await self.get_presence(user_id)
        has_active = any(p.state in (PresenceState.ACTIVE, PresenceState.IDLE) for p in presences)

        status_text = "Kairo session active" if has_active else "Offline"
        active_count = sum(1 for p in presences if p.state in (PresenceState.ACTIVE, PresenceState.IDLE))

        return UserOnlineStatus(
            user_id=user_id,
            status_text=status_text,
            active_sessions_count=active_count,
            presence=presences,
        )
