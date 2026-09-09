"""Explicit device trust management and security invariant verification (Spec 12, 13, 14, 133)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.devices.models import DeviceModel
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.schemas import DeviceStatus, DeviceTrustStatus, IdentityErrorCode
from app.security.exceptions import SecurityPolicyViolationError, TenantIsolationError

logger = logging.getLogger("kairo.identity.trust")


class DeviceTrustManager:
    """Manages explicit device trust transitions, trust expiration, and trust revocation ripples."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def update_trust(
        self,
        user_id: str,
        device_id: str,
        target_trust: DeviceTrustStatus,
        expires_in_days: int = 90,
    ) -> DeviceModel:
        """Explicitly set device trust status enforcing tenant ownership and revocation ripple (Spec 12, 14)."""
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            raise KeyError(f"Device '{device_id}' not found.")

        if device.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Device '{device_id}' belongs to another user.")

        now = datetime.now(UTC)

        if target_trust == DeviceTrustStatus.REVOKED:
            # Revocation ripple: call revocation coordinator
            from app.identity.revocation import RevocationCoordinator
            coordinator = RevocationCoordinator(self.db)
            await coordinator.revoke_device(user_id=user_id, device_id=device_id, reason="Explicit trust revocation")
            await self.db.refresh(device)
            return device

        # Update trust status
        device.trust_status = target_trust.value
        if target_trust == DeviceTrustStatus.TRUSTED:
            device.trust_expires_at = now + timedelta(days=expires_in_days)
        else:
            device.trust_expires_at = None

        await self.db.commit()
        await self.db.refresh(device)

        logger.info("Device '%s' trust status updated to '%s' (expires: %s)", device.id, device.trust_status, device.trust_expires_at)

        # Emit device.trusted event
        if target_trust == DeviceTrustStatus.TRUSTED:
            try:
                from app.events import event_bus
                await event_bus.publish(
                    event_bus.publisher.create_event(
                        event_type="device.trusted",
                        source="identity",
                        payload={"device_id": device.id, "device_name": device.device_name},
                        user_id=user_id,
                    )
                )
            except Exception:
                pass

        return device

    async def verify_device_trusted(self, user_id: str, device_id: str) -> bool:
        """Verify device is currently trusted without expired trust (Spec 133)."""
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            return False

        if device.user_id != user_id:
            return False

        try:
            IdentityPolicyEnforcer.enforce_device_trust(
                device_status=device.status,
                trust_status=device.trust_status,
                trust_expires_at=device.trust_expires_at,
                required_trust=DeviceTrustStatus.TRUSTED,
            )
            return True
        except SecurityPolicyViolationError:
            return False
