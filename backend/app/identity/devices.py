"""Device registration, pairing, and capability governance for Kairo Identity (Spec 10-20, 60-62)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.devices.models import DeviceModel
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.schemas import (
    ClientType,
    DeviceCapability,
    DevicePairingConsumeRequest,
    DevicePairingRequest,
    DevicePairingResponse,
    DeviceStatus,
    DeviceTrustStatus,
    IdentityErrorCode,
)
from app.identity.tokens import generate_pairing_code, generate_session_token, hash_token, verify_token
from app.security.exceptions import (
    CapabilityDisabledError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)

logger = logging.getLogger("kairo.identity.devices")


class IdentityDeviceManager:
    """Manages device lifecycle, hardware capabilities, pairing secrets, and companion validation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.pairing_ttl = getattr(self.settings, "KAIRO_IDENTITY_PAIRING_TTL_SECONDS", 600)
        self.max_devices = getattr(self.settings, "KAIRO_IDENTITY_MAX_DEVICES_PER_USER", 15)

    async def register_device(
        self,
        user_id: str,
        device_name: str,
        os_name: str,
        client_type: ClientType = ClientType.LOCAL_COMPANION,
        os_version: str = "unknown",
        companion_version: str = "1.1.0",
        capabilities: list[str] | None = None,
        public_key: str | None = None,
    ) -> DeviceModel:
        """Register a new device companion enforcing tenant boundaries and limits (Spec 15, 120)."""
        # Enforce max devices per user
        count_stmt = select(DeviceModel).where(
            DeviceModel.user_id == user_id,
            DeviceModel.status != DeviceStatus.REVOKED.value,
        )
        res = await self.db.execute(count_stmt)
        existing = res.scalars().all()
        if len(existing) >= self.max_devices:
            raise SecurityPolicyViolationError(
                f"Maximum registered devices limit ({self.max_devices}) reached for user."
            )

        # Validate advertised capabilities (Spec 19)
        valid_caps = []
        if capabilities:
            allowed_names = {c.value for c in DeviceCapability}
            for cap in capabilities:
                cap_clean = cap.strip().upper()
                if cap_clean in allowed_names:
                    valid_caps.append(cap_clean)

        raw_token = generate_session_token()
        token_hash = hash_token(raw_token)
        device_id = f"dev_{uuid.uuid4().hex[:16]}"
        now = datetime.now(UTC)

        device = DeviceModel(
            id=device_id,
            user_id=user_id,
            device_name=device_name,
            os_name=os_name.lower(),
            os_version=os_version,
            companion_version=companion_version,
            status=DeviceStatus.ACTIVE.value,
            client_type=client_type.value if hasattr(client_type, "value") else str(client_type),
            trust_status=DeviceTrustStatus.UNTRUSTED.value,  # Trust must be explicit (Spec 12)
            capabilities=valid_caps,
            public_key=public_key,
            credentials_hash=token_hash,
            created_at=now,
            last_seen_at=now,
        )
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)

        logger.info("Registered device '%s' (%s) for user '%s'. Trust: UNTRUSTED", device.id, device.device_name, user_id)

        # Emit device.registered event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="device.registered",
                    source="identity",
                    payload={"device_id": device.id, "device_name": device.device_name},
                    user_id=user_id,
                )
            )
        except Exception:
            pass

        return device

    async def initiate_pairing(self, user_id: str, request: DevicePairingRequest) -> DevicePairingResponse:
        """Issue a short-lived, single-use pairing code for desktop/companion pairing (Spec 16, 17, 18)."""
        pairing_code = generate_pairing_code()
        code_hash = hash_token(pairing_code)
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.pairing_ttl)

        device_name = request.device_name or f"Companion-{pairing_code.split('-')[1]}"
        device_id = f"dev_{uuid.uuid4().hex[:16]}"

        caps = [c.value for c in request.capabilities]

        device = DeviceModel(
            id=device_id,
            user_id=user_id,
            device_name=device_name,
            os_name="pending",
            os_version="pending",
            companion_version="1.1.0",
            status=DeviceStatus.PENDING.value,
            client_type=request.client_type.value,
            trust_status=DeviceTrustStatus.PENDING.value,
            pairing_code_hash=code_hash,
            pairing_expires_at=expires_at,
            capabilities=caps,
            created_at=now,
            last_seen_at=now,
        )
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)

        logger.info("Initiated pairing for device '%s' (expires: %s)", device.id, expires_at)

        return DevicePairingResponse(
            pairing_code=pairing_code,
            device_id=device.id,
            expires_at=expires_at,
            instructions="Enter this pairing code into your Kairo Desktop Companion within 10 minutes.",
        )

    async def consume_pairing(self, user_id: str, request: DevicePairingConsumeRequest) -> dict[str, Any]:
        """Consume a pairing code, enforcing expiration and replay protection (Spec 17, 18)."""
        device = await self.db.get(DeviceModel, request.device_id)
        if not device:
            raise KeyError(f"Device '{request.device_id}' not found.")

        if device.user_id != user_id:
            raise TenantIsolationError("Pairing code does not belong to the current authenticated user.")

        if not device.pairing_code_hash:
            logger.warning("Pairing replay attempt: code already consumed for device '%s'.", device.id)
            raise SecurityPolicyViolationError("Pairing code has already been consumed or is invalid.")

        now = datetime.now(UTC)
        if device.pairing_expires_at:
            p_exp = device.pairing_expires_at if device.pairing_expires_at.tzinfo is not None else device.pairing_expires_at.replace(tzinfo=UTC)
            if now > p_exp:
                logger.warning("Pairing code expired for device '%s'.", device.id)
                device.pairing_code_hash = None
                await self.db.commit()
                raise SecurityPolicyViolationError("Pairing code has expired.")

        # Verify pairing code constant-time
        if not verify_token(request.pairing_code, device.pairing_code_hash):
            logger.warning("Invalid pairing code entered for device '%s'.", device.id)
            raise SecurityPolicyViolationError("Invalid pairing code.")

        # Success: consume code immediately so it cannot be replayed (Spec 18)
        device.pairing_code_hash = None
        device.pairing_expires_at = None
        device.status = DeviceStatus.ACTIVE.value
        device.last_seen_at = now
        if request.public_key:
            device.public_key = request.public_key

        raw_device_token = generate_session_token()
        device.credentials_hash = hash_token(raw_device_token)
        await self.db.commit()
        await self.db.refresh(device)

        logger.info("Pairing completed for device '%s'. Device activated.", device.id)

        # Emit device.connected event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="device.connected",
                    source="identity",
                    payload={"device_id": device.id, "device_name": device.device_name},
                    user_id=user_id,
                )
            )
        except Exception:
            pass

        return {
            "device_id": device.id,
            "device_name": device.device_name,
            "status": device.status,
            "trust_status": device.trust_status,
            "device_token": raw_device_token,
        }

    async def get_device(self, user_id: str, device_id: str) -> DeviceModel:
        """Retrieve device and validate user ownership."""
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            raise KeyError(f"Device '{device_id}' not found.")
        IdentityPolicyEnforcer.enforce_tenant_isolation(user_id, device.user_id, f"Device '{device_id}'")
        return device

    async def mark_offline(self, device_id: str) -> None:
        """Mark device OFFLINE without treating it as REVOKED (Spec 11)."""
        device = await self.db.get(DeviceModel, device_id)
        if device and device.status != DeviceStatus.REVOKED.value:
            device.status = DeviceStatus.OFFLINE.value
            await self.db.commit()
            logger.info("Device '%s' marked OFFLINE.", device_id)
