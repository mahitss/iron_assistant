"""Entity projections mapping authoritative relational records into World Model entities (Task 32, Spec 124, 125)."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.devices.models import DeviceModel
from app.tasks.models import TaskModel
from app.world.entities import (
    ConfidenceLevel,
    EntityType,
    ObservationType,
    WorldEntitySchema,
    generate_entity_id,
)
from app.world.freshness import FreshnessPolicy
from app.world.state import DeviceState, TaskOperationalState


class EntityProjectionService:
    """Projects authoritative existing table records into unified World Model entities."""

    @classmethod
    def project_device(cls, device: DeviceModel) -> WorldEntitySchema:
        """Project a DeviceModel row into a WorldEntitySchema (Spec 12)."""
        observed_at = device.updated_at or device.created_at or datetime.now(UTC)
        expires_at = FreshnessPolicy.compute_expiration(EntityType.DEVICE, observed_at)

        # Map device status to structured state
        raw_status = (device.status or "UNKNOWN").upper()
        if raw_status == "REVOKED":
            st = DeviceState.REVOKED.value
        elif raw_status == "ACTIVE":
            st = DeviceState.CONNECTED.value
        elif raw_status in ("DISABLED", "DISCONNECTED"):
            st = DeviceState.DISCONNECTED.value
        else:
            st = DeviceState.UNKNOWN.value

        is_stale = FreshnessPolicy.is_stale(observed_at, expires_at, EntityType.DEVICE)

        return WorldEntitySchema(
            id=generate_entity_id(EntityType.DEVICE, device.user_id, "local_companion", device.id),
            type=EntityType.DEVICE,
            name=device.device_name or f"Device {device.id[:8]}",
            owner_id=device.user_id,
            project_id=None,
            source="local_companion",
            source_id=device.id,
            state=st,
            state_version=None,
            observation_type=ObservationType.OBSERVED,
            confidence=ConfidenceLevel.HIGH,
            observed_at=observed_at,
            expires_at=expires_at,
            metadata={
                "os_name": device.os_name,
                "os_version": device.os_version,
                "companion_version": device.companion_version,
                "client_type": getattr(device, "client_type", "LOCAL_COMPANION"),
                "trust_status": getattr(device, "trust_status", "UNTRUSTED"),
                "declared_capabilities": getattr(device, "capabilities", []),
                "authorization": {
                    "computer_control": getattr(device, "computer_control_enabled", False),
                    "voice": getattr(device, "voice_enabled", False),
                    "camera": getattr(device, "camera_enabled", False),
                    "filesystem": getattr(device, "filesystem_enabled", False),
                },
            },
            is_stale=is_stale,
        )

    @classmethod
    def project_task(cls, task: TaskModel) -> WorldEntitySchema:
        """Project a TaskModel row into a WorldEntitySchema (Spec 10)."""
        observed_at = task.updated_at or task.created_at or datetime.now(UTC)
        expires_at = FreshnessPolicy.compute_expiration(EntityType.TASK, observed_at)

        is_stale = FreshnessPolicy.is_stale(observed_at, expires_at, EntityType.TASK)

        return WorldEntitySchema(
            id=generate_entity_id(EntityType.TASK, task.user_id, "task_engine", task.id),
            type=EntityType.TASK,
            name=f"Task: {task.objective[:50]}",
            owner_id=task.user_id,
            project_id=task.project_id,
            source="task_engine",
            source_id=task.id,
            state=(task.status or "UNKNOWN").upper(),
            state_version=None,
            observation_type=ObservationType.OBSERVED,
            confidence=ConfidenceLevel.HIGH,
            observed_at=observed_at,
            expires_at=expires_at,
            metadata={
                "priority": task.priority,
                "autonomy_level": task.autonomy_level,
                "current_step_id": task.current_step_id,
            },
            is_stale=is_stale,
        )
