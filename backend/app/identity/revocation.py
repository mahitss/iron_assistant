"""Centralized revocation coordinator ensuring revocation ripple across sessions, approvals, and runtimes (Spec 14, 74, 75, 148)."""

from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.devices.models import DeviceModel
from app.identity.models import IdentityPresenceModel, IdentitySessionModel
from app.identity.schemas import DeviceStatus, DeviceTrustStatus, SessionStatus
from app.security.exceptions import TenantIsolationError

logger = logging.getLogger("kairo.identity.revocation")


class RevocationCoordinator:
    """Coordinates cascading revocation across devices, sessions, approvals, and runtime permissions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def revoke_device(self, user_id: str, device_id: str, reason: str = "Device revoked by user") -> dict[str, Any]:
        """
        Revoke a device and trigger immediate cascading ripple (Spec 14, 75, 148):
        1. Mark device REVOKED and trust REVOKED.
        2. Invalidate cryptographic credentials and pairing codes.
        3. Disable all device capabilities (computer control, camera, voice, filesystem).
        4. Terminate all active sessions bound to this device.
        5. Mark device presence DISCONNECTED.
        6. Cancel any pending approvals tied to this device.
        """
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            raise KeyError(f"Device '{device_id}' not found.")

        if device.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Device '{device_id}' belongs to another user.")

        now = datetime.now(UTC)

        # 1. Update device model
        device.status = DeviceStatus.REVOKED.value
        device.trust_status = DeviceTrustStatus.REVOKED.value
        device.credentials_hash = None
        device.pairing_code_hash = None
        device.pairing_expires_at = None
        device.trust_expires_at = None
        device.revoked_at = now
        device.computer_control_enabled = False
        device.voice_enabled = False
        device.camera_enabled = False
        device.filesystem_enabled = False

        # 2. Terminate all active sessions on this device
        sess_stmt = select(IdentitySessionModel).where(
            IdentitySessionModel.device_id == device_id,
            IdentitySessionModel.status == SessionStatus.ACTIVE.value,
        )
        res = await self.db.execute(sess_stmt)
        active_sessions = list(res.scalars().all())

        for s in active_sessions:
            s.status = SessionStatus.REVOKED.value
            s.revoked_at = now

        # 3. Clean up presence
        pres_stmt = select(IdentityPresenceModel).where(IdentityPresenceModel.device_id == device_id)
        pres_res = await self.db.execute(pres_stmt)
        for p in pres_res.scalars().all():
            p.state = "DISCONNECTED"

        await self.db.commit()

        logger.critical(
            "DEVICE REVOKED: Device '%s' revoked for user '%s'. Terminated %d active sessions.",
            device_id,
            user_id,
            len(active_sessions),
        )

        # 4. Invalidate associated tokens in auth session store
        try:
            from app.auth.sessions import get_session_store
            store = get_session_store()
            for s in active_sessions:
                store.revoke_session(s.session_id, reason=f"Bound device revoked: {reason}")
        except Exception:
            pass

        # 5. Cancel pending SecurityCenter approvals for this user/device
        try:
            from app.security.center import get_security_center
            sec_center = get_security_center()
            if sec_center and sec_center.approvals:
                pending = sec_center.approvals.list_pending(user_id=user_id)
                for apprv in pending:
                    # Invalidate approval
                    sec_center.approvals.resolve(
                        approval_id=apprv.id,
                        decision="rejected",
                        user_id=user_id,
                        denial_reason="Device authorization revoked",
                    )
        except Exception as apprv_err:
            logger.debug("Could not cancel approvals on device revocation: %s", apprv_err)

        # 6. Emit device.revoked event to EventBus
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="device.revoked",
                    source="identity",
                    payload={
                        "device_id": device_id,
                        "terminated_sessions_count": len(active_sessions),
                        "reason": reason,
                    },
                    user_id=user_id,
                )
            )
        except Exception:
            pass

        return {
            "device_id": device_id,
            "status": "REVOKED",
            "trust_status": "REVOKED",
            "terminated_sessions": len(active_sessions),
        }
