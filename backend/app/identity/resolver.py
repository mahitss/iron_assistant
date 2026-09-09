"""Identity, Session, Device, and Continuity context resolver with strict ambiguity handling (Spec 40, 41, 65, 66, 152, 153)."""

from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.devices.models import DeviceModel
from app.identity.models import IdentityPresenceModel, IdentitySessionModel
from app.identity.schemas import DeviceStatus, DeviceTrustStatus, IdentityErrorCode, SessionStatus
from app.security.exceptions import TenantIsolationError

logger = logging.getLogger("kairo.identity.resolver")


class IdentityResolver:
    """Resolves continuity context and safely detects ambiguous targets without guessing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def resolve_task_continuity(
        self, user_id: str, requested_task_id: str | None = None, project_id: str | None = None
    ) -> dict[str, Any]:
        """
        Resolve active task continuity across sessions (Spec 27, 40, 41, 152).
        If user has multiple active tasks and says 'Continue', do NOT guess — ask which one.
        """
        # If user explicitly requested a task
        if requested_task_id:
            try:
                from app.tasks.models import TaskModel
                task = await self.db.get(TaskModel, requested_task_id)
                if not task or task.user_id != user_id:
                    return {"ambiguous": False, "task": None, "error": "Task not found or access denied."}
                return {
                    "ambiguous": False,
                    "task_id": task.id,
                    "objective": task.objective,
                    "status": task.status,
                }
            except ImportError:
                return {"ambiguous": False, "task_id": requested_task_id}

        # Query all active/running/waiting tasks for this user
        try:
            from app.tasks.models import TaskModel
            stmt = select(TaskModel).where(
                TaskModel.user_id == user_id,
                TaskModel.status.in_(["RUNNING", "WAITING_APPROVAL", "WAITING_USER", "QUEUED"]),
            )
            if project_id:
                stmt = stmt.where(TaskModel.project_id == project_id)
            stmt = stmt.order_by(TaskModel.created_at.desc())

            res = await self.db.execute(stmt)
            active_tasks = list(res.scalars().all())

            if len(active_tasks) == 0:
                return {"ambiguous": False, "task_id": None}

            if len(active_tasks) == 1:
                # Exactly one active task: seamless continuity
                single = active_tasks[0]
                return {
                    "ambiguous": False,
                    "task_id": single.id,
                    "objective": single.objective,
                    "status": single.status,
                }

            # Multiple active tasks exist: DO NOT GUESS (Spec 41, 152)
            task_options = [
                {"task_id": t.id, "objective": t.objective[:80], "status": t.status}
                for t in active_tasks
            ]
            logger.info("Ambiguous task continuity detected for user '%s' (%d active tasks). Asking user.", user_id, len(active_tasks))
            return {
                "ambiguous": True,
                "error_code": IdentityErrorCode.AMBIGUOUS_TARGET.value,
                "prompt": "You have multiple active tasks running. Which task would you like to continue?",
                "options": task_options,
            }

        except ImportError:
            return {"ambiguous": False, "task_id": None}

    async def resolve_device_target(
        self,
        user_id: str,
        explicit_device_id: str | None = None,
        required_capability: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolve device target for hardware-dependent actions (Spec 65, 66, 153).
        If user has multiple active devices supporting capability, DO NOT GUESS — ask which device.
        """
        if explicit_device_id:
            device = await self.db.get(DeviceModel, explicit_device_id)
            if not device or device.user_id != user_id:
                raise TenantIsolationError(f"Device '{explicit_device_id}' not found or belongs to another user.")
            if device.status == DeviceStatus.REVOKED.value:
                return {"ambiguous": False, "device": None, "error_code": IdentityErrorCode.DEVICE_REVOKED.value}
            return {"ambiguous": False, "device_id": device.id, "device_name": device.device_name}

        # Query active trusted devices for user
        stmt = select(DeviceModel).where(
            DeviceModel.user_id == user_id,
            DeviceModel.status == DeviceStatus.ACTIVE.value,
            DeviceModel.trust_status == DeviceTrustStatus.TRUSTED.value,
        )
        res = await self.db.execute(stmt)
        active_devices = list(res.scalars().all())

        if required_capability:
            req = required_capability.upper()
            active_devices = [
                d for d in active_devices
                if any(c.upper() == req for c in (d.capabilities or []))
            ]

        if len(active_devices) == 0:
            return {
                "ambiguous": False,
                "device_id": None,
                "error_code": IdentityErrorCode.DEVICE_UNAVAILABLE.value,
                "prompt": "No authorized, trusted devices are currently online supporting this capability.",
            }

        if len(active_devices) == 1:
            single = active_devices[0]
            return {
                "ambiguous": False,
                "device_id": single.id,
                "device_name": single.device_name,
            }

        # Multiple candidate devices: DO NOT GUESS (Spec 66, 153)
        device_options = [
            {"device_id": d.id, "device_name": d.device_name, "os_name": d.os_name}
            for d in active_devices
        ]
        logger.info("Ambiguous device target detected for user '%s' (%d devices). Asking user.", user_id, len(active_devices))
        return {
            "ambiguous": True,
            "error_code": IdentityErrorCode.AMBIGUOUS_DEVICE.value,
            "prompt": "Multiple authorized devices are available. Which device would you like to use?",
            "options": device_options,
        }
