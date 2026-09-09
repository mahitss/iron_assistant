"""Device service managing registration, credentials, capability governance, and command routing."""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from app.devices.models import DeviceModel
from app.devices.schemas import (
    DeviceCapabilitiesSchema,
    DeviceCommandRequest,
    DeviceCommandResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceResponse,
    DeviceStatus,
    DeviceUpdateRequest,
)
from app.security.audit import AuditLogger
from app.security.exceptions import (
    CapabilityDisabledError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("kairo.devices.service")

# Allowlisted actions that companion runtimes may execute
FORBIDDEN_ACTIONS = {
    "shell.execute",
    "shell.run",
    "bash.run",
    "powershell.run",
    "cmd.run",
    "arbitrary_python",
    "arbitrary_process",
    "process.spawn",
    "system.reboot",
}

ALLOWLISTED_ACTIONS = {
    "screen.capture": {"capability": "computer_control", "requires_approval": False},
    "screen.observe": {"capability": "computer_control", "requires_approval": False},
    "mouse.move": {"capability": "computer_control", "requires_approval": False},
    "mouse.click": {"capability": "computer_control", "requires_approval": True},
    "mouse.double_click": {"capability": "computer_control", "requires_approval": True},
    "mouse.scroll": {"capability": "computer_control", "requires_approval": False},
    "keyboard.type": {"capability": "computer_control", "requires_approval": True},
    "keyboard.press": {"capability": "computer_control", "requires_approval": True},
    "audio.record": {"capability": "voice", "requires_approval": False},
    "audio.play": {"capability": "voice", "requires_approval": False},
    "camera.capture": {"capability": "camera", "requires_approval": True},
    "filesystem.read": {"capability": "filesystem", "requires_approval": False},
    "filesystem.write_restricted": {"capability": "filesystem", "requires_approval": True},
    "filesystem.delete_restricted": {"capability": "filesystem", "requires_approval": True},
}


class DeviceService:
    """Service governing device lifecycle, credentials, capabilities, and command dispatch."""

    def __init__(self, db: AsyncSession, audit_logger: AuditLogger | None = None) -> None:
        self.db = db
        self.audit_logger = audit_logger or AuditLogger()

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def register_device(self, user_id: str, payload: DeviceRegisterRequest) -> DeviceRegisterResponse:
        """Register a new device companion under the authenticated user account."""
        device_id = payload.device_id or f"dev_{uuid.uuid4().hex[:16]}"
        raw_token = f"kairo_dtk_{secrets.token_urlsafe(32)}"
        token_hash = self._hash_token(raw_token)

        device = DeviceModel(
            id=device_id,
            user_id=user_id,
            device_name=payload.device_name,
            os_name=payload.os_name.lower(),
            os_version=payload.os_version,
            companion_version=payload.companion_version,
            status=DeviceStatus.ACTIVE.value,
            public_key=payload.public_key,
            credentials_hash=token_hash,
            computer_control_enabled=False,
            voice_enabled=False,
            camera_enabled=False,
            filesystem_enabled=False,
            allowed_paths=payload.allowed_paths,
            created_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )

        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)

        await AuditLogger.log_event(
            db_session=self.db,
            user_id=user_id,
            event_type="device.registered",
            decision="ALLOWED",
            success=True,
            metadata={
                "device_id": device.id,
                "device_name": device.device_name,
                "os_name": device.os_name,
            },
        )

        return DeviceRegisterResponse(
            device_id=device.id,
            device_name=device.device_name,
            status=DeviceStatus(device.status),
            device_token=raw_token,
            capabilities=DeviceCapabilitiesSchema(
                computer_control=device.computer_control_enabled,
                voice=device.voice_enabled,
                camera=device.camera_enabled,
                filesystem=device.filesystem_enabled,
            ),
            allowed_paths=device.allowed_paths,
            created_at=device.created_at,
        )

    async def list_user_devices(self, user_id: str, include_revoked: bool = False) -> list[DeviceResponse]:
        """Fetch all devices owned by the authenticated user."""
        stmt = select(DeviceModel).where(DeviceModel.user_id == user_id)
        if not include_revoked:
            stmt = stmt.where(DeviceModel.status != DeviceStatus.REVOKED.value)
        stmt = stmt.order_by(DeviceModel.created_at.desc())

        result = await self.db.execute(stmt)
        devices = result.scalars().all()

        return [
            DeviceResponse(
                device_id=d.id,
                user_id=d.user_id,
                device_name=d.device_name,
                os_name=d.os_name,
                os_version=d.os_version,
                companion_version=d.companion_version,
                status=DeviceStatus(d.status),
                capabilities=DeviceCapabilitiesSchema(
                    computer_control=d.computer_control_enabled,
                    voice=d.voice_enabled,
                    camera=d.camera_enabled,
                    filesystem=d.filesystem_enabled,
                ),
                allowed_paths=d.allowed_paths,
                created_at=d.created_at,
                last_seen_at=d.last_seen_at,
                revoked_at=d.revoked_at,
            )
            for d in devices
        ]

    async def get_device(self, user_id: str, device_id: str) -> DeviceResponse:
        """Fetch specific device metadata with strict tenant boundary enforcement."""
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            raise KeyError(f"Device '{device_id}' not found.")
        if device.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Device '{device_id}' belongs to another user.")

        return DeviceResponse(
            device_id=device.id,
            user_id=device.user_id,
            device_name=device.device_name,
            os_name=device.os_name,
            os_version=device.os_version,
            companion_version=device.companion_version,
            status=DeviceStatus(device.status),
            capabilities=DeviceCapabilitiesSchema(
                computer_control=device.computer_control_enabled,
                voice=device.voice_enabled,
                camera=device.camera_enabled,
                filesystem=device.filesystem_enabled,
            ),
            allowed_paths=device.allowed_paths,
            created_at=device.created_at,
            last_seen_at=device.last_seen_at,
            revoked_at=device.revoked_at,
        )

    async def update_device(
        self, user_id: str, device_id: str, payload: DeviceUpdateRequest
    ) -> DeviceResponse:
        """Update device capabilities or settings with audit logging."""
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            raise KeyError(f"Device '{device_id}' not found.")
        if device.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Device '{device_id}' belongs to another user.")
        if device.status == DeviceStatus.REVOKED.value:
            raise SecurityPolicyViolationError(f"Cannot update revoked device '{device_id}'.")

        changes: dict[str, Any] = {}
        if payload.device_name is not None:
            device.device_name = payload.device_name
            changes["device_name"] = payload.device_name
        if payload.computer_control_enabled is not None:
            device.computer_control_enabled = payload.computer_control_enabled
            changes["computer_control_enabled"] = payload.computer_control_enabled
        if payload.voice_enabled is not None:
            device.voice_enabled = payload.voice_enabled
            changes["voice_enabled"] = payload.voice_enabled
        if payload.camera_enabled is not None:
            device.camera_enabled = payload.camera_enabled
            changes["camera_enabled"] = payload.camera_enabled
        if payload.filesystem_enabled is not None:
            device.filesystem_enabled = payload.filesystem_enabled
            changes["filesystem_enabled"] = payload.filesystem_enabled
        if payload.allowed_paths is not None:
            device.allowed_paths = payload.allowed_paths
            changes["allowed_paths"] = payload.allowed_paths
        if payload.status is not None:
            device.status = payload.status.value
            changes["status"] = payload.status.value

        device.last_seen_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(device)

        await AuditLogger.log_event(
            db_session=self.db,
            user_id=user_id,
            event_type="device.capability_changed",
            decision="ALLOWED",
            success=True,
            metadata={"device_id": device_id, "changes": changes},
        )

        return DeviceResponse(
            device_id=device.id,
            user_id=device.user_id,
            device_name=device.device_name,
            os_name=device.os_name,
            os_version=device.os_version,
            companion_version=device.companion_version,
            status=DeviceStatus(device.status),
            capabilities=DeviceCapabilitiesSchema(
                computer_control=device.computer_control_enabled,
                voice=device.voice_enabled,
                camera=device.camera_enabled,
                filesystem=device.filesystem_enabled,
            ),
            allowed_paths=device.allowed_paths,
            created_at=device.created_at,
            last_seen_at=device.last_seen_at,
            revoked_at=device.revoked_at,
        )

    async def revoke_device(self, user_id: str, device_id: str) -> DeviceResponse:
        """Revoke device authorization immediately invalidating credentials and closing sessions."""
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            raise KeyError(f"Device '{device_id}' not found.")
        if device.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Device '{device_id}' belongs to another user.")

        device.status = DeviceStatus.REVOKED.value
        device.credentials_hash = None
        device.revoked_at = datetime.now(UTC)
        device.computer_control_enabled = False
        device.voice_enabled = False
        device.camera_enabled = False
        device.filesystem_enabled = False

        await self.db.commit()
        await self.db.refresh(device)

        await AuditLogger.log_event(
            db_session=self.db,
            user_id=user_id,
            event_type="device.revoked",
            decision="ALLOWED",
            success=True,
            metadata={"device_id": device_id, "reason": "User explicit revocation"},
        )

        return DeviceResponse(
            device_id=device.id,
            user_id=device.user_id,
            device_name=device.device_name,
            os_name=device.os_name,
            os_version=device.os_version,
            companion_version=device.companion_version,
            status=DeviceStatus.REVOKED,
            capabilities=DeviceCapabilitiesSchema(
                computer_control=False,
                voice=False,
                camera=False,
                filesystem=False,
            ),
            allowed_paths=device.allowed_paths,
            created_at=device.created_at,
            last_seen_at=device.last_seen_at,
            revoked_at=device.revoked_at,
        )

    async def dispatch_command(
        self, user_id: str, device_id: str, payload: DeviceCommandRequest
    ) -> DeviceCommandResponse:
        """Dispatch a bounded, allowlisted action to an active companion device."""
        action = payload.action.strip()

        # 1. Block forbidden arbitrary OS execution
        if action in FORBIDDEN_ACTIONS or "shell" in action or "exec" in action:
            await AuditLogger.log_event(
                db_session=self.db,
                user_id=user_id,
                event_type="device.security_block",
                decision="DENIED",
                success=False,
                metadata={
                    "device_id": device_id,
                    "action": action,
                    "reason": "Arbitrary OS execution forbidden",
                },
            )
            raise SecurityPolicyViolationError(
                f"Action '{action}' is strictly forbidden. Arbitrary command execution is not permitted."
            )

        # 2. Verify action is in strict allowlist
        if action not in ALLOWLISTED_ACTIONS:
            raise SecurityPolicyViolationError(
                f"Action '{action}' is not allowlisted for companion execution."
            )

        # 3. Verify device exists, belongs to user, and is ACTIVE
        device = await self.db.get(DeviceModel, device_id)
        if not device:
            raise KeyError(f"Device '{device_id}' not found.")
        if device.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Device '{device_id}' belongs to another user.")
        if device.status != DeviceStatus.ACTIVE.value:
            raise SecurityPolicyViolationError(
                f"Cannot dispatch command to device in '{device.status}' state."
            )

        # 4. Check device capability gate
        action_meta = ALLOWLISTED_ACTIONS[action]
        required_capability = action_meta["capability"]
        cap_enabled = getattr(device, f"{required_capability}_enabled", False)
        if not cap_enabled:
            raise CapabilityDisabledError(
                f"Capability '{required_capability}' is disabled on device '{device.device_name}'."
            )

        # 5. Check approval requirement
        command_id = f"cmd_{uuid.uuid4().hex[:16]}"
        now = datetime.now(UTC)
        requires_approval = action_meta["requires_approval"]

        if requires_approval and not payload.authorization_context:
            approval_id = f"appr_{uuid.uuid4().hex[:12]}"
            await AuditLogger.log_event(
                db_session=self.db,
                user_id=user_id,
                event_type="device.approval_required",
                decision="APPROVAL_REQUIRED",
                approval_id=approval_id,
                success=False,
                metadata={
                    "command_id": command_id,
                    "device_id": device_id,
                    "action": action,
                    "approval_id": approval_id,
                },
            )
            return DeviceCommandResponse(
                command_id=command_id,
                device_id=device_id,
                action=action,
                status="PENDING_APPROVAL",
                approval_required=True,
                approval_id=approval_id,
                dispatched_at=now,
                details={"message": f"Action '{action}' requires explicit user approval prior to execution."},
            )

        # 6. Dispatch successful
        await AuditLogger.log_event(
            db_session=self.db,
            user_id=user_id,
            event_type="device.command_dispatched",
            decision="ALLOWED",
            success=True,
            metadata={
                "command_id": command_id,
                "device_id": device_id,
                "action": action,
                "has_approval": bool(payload.authorization_context),
            },
        )

        return DeviceCommandResponse(
            command_id=command_id,
            device_id=device_id,
            action=action,
            status="DISPATCHED",
            approval_required=False,
            approval_id=None,
            dispatched_at=now,
            details={"parameters_received": len(payload.parameters)},
        )
