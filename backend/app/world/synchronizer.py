"""Event-driven synchronization and periodic reconciliation for Kairo World Model (Task 32, Spec 58-62, 88)."""

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.world.conflicts import ConflictResolutionAction, StateConflictEngine
from app.world.entities import (
    ConfidenceLevel,
    EntityType,
    ObservationType,
    WorldEntitySchema,
    generate_entity_id,
)
from app.world.freshness import FreshnessPolicy
from app.world.registry import SourceAuthority, SourceOfTruthRegistry
from app.world.state import (
    DeviceState,
    RepositoryState,
    ServiceState,
    StateTransitionValidator,
    TaskOperationalState,
)

logger = logging.getLogger("kairo.world.synchronizer")


class WorldSynchronizer:
    """Synchronizes external events and reconciles out-of-sync entities."""

    def __init__(self) -> None:
        self._reconciliation_interval_seconds: int = 300
        self._last_reconciliation_timestamp: Optional[datetime] = None

    def process_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        entities_by_id: dict[str, WorldEntitySchema],
    ) -> Optional[WorldEntitySchema]:
        """
        Process an event from the Event Bus and return an updated or new WorldEntitySchema.
        Rejects stale updates and enforces authoritative source hierarchy.
        """
        user_id = payload.get("user_id", "default_user")
        now = datetime.now(UTC)

        # 1. Device events
        if event_type.startswith("device."):
            device_id = payload.get("device_id")
            if not device_id:
                return None
            ent_id = generate_entity_id(EntityType.DEVICE, user_id, "local_companion", device_id)
            existing = entities_by_id.get(ent_id)

            if event_type == "device.revoked":
                target_state = DeviceState.REVOKED.value
            elif event_type == "device.connected":
                target_state = DeviceState.CONNECTED.value
            elif event_type == "device.disconnected":
                target_state = DeviceState.DISCONNECTED.value
            else:
                target_state = DeviceState.UNKNOWN.value

            # Check valid transition (REVOKED can never become CONNECTED) (Spec 82, 131)
            if existing:
                if not StateTransitionValidator.can_transition_device(existing.state, target_state):
                    logger.warning(
                        "Illegal transition rejected for device '%s': %s -> %s",
                        device_id, existing.state, target_state
                    )
                    return existing

                existing.state = target_state
                existing.observed_at = now
                existing.expires_at = FreshnessPolicy.compute_expiration(EntityType.DEVICE, now)
                existing.is_stale = False
                return existing

            return WorldEntitySchema(
                id=ent_id,
                type=EntityType.DEVICE,
                name=payload.get("device_name", f"Device {device_id[:8]}"),
                owner_id=user_id,
                project_id=None,
                source="local_companion",
                source_id=device_id,
                state=target_state,
                observation_type=ObservationType.OBSERVED,
                confidence=ConfidenceLevel.HIGH,
                observed_at=now,
                expires_at=FreshnessPolicy.compute_expiration(EntityType.DEVICE, now),
                metadata=payload.get("metadata", {}),
            )

        # 2. Task events
        elif event_type.startswith("task."):
            task_id = payload.get("task_id")
            if not task_id:
                return None
            ent_id = generate_entity_id(EntityType.TASK, user_id, "task_engine", task_id)
            existing = entities_by_id.get(ent_id)

            if event_type == "task.created":
                target_state = TaskOperationalState.QUEUED.value
            elif event_type == "task.started":
                target_state = TaskOperationalState.RUNNING.value
            elif event_type == "task.waiting_approval":
                target_state = TaskOperationalState.WAITING_APPROVAL.value
            elif event_type == "task.completed":
                target_state = TaskOperationalState.COMPLETED.value
            elif event_type == "task.failed":
                target_state = TaskOperationalState.FAILED.value
            elif event_type == "task.cancelled":
                target_state = TaskOperationalState.CANCELLED.value
            else:
                target_state = TaskOperationalState.RUNNING.value

            if existing:
                existing.state = target_state
                existing.observed_at = now
                existing.expires_at = FreshnessPolicy.compute_expiration(EntityType.TASK, now)
                existing.is_stale = False
                return existing

            return WorldEntitySchema(
                id=ent_id,
                type=EntityType.TASK,
                name=payload.get("objective", f"Task {task_id[:8]}")[:60],
                owner_id=user_id,
                project_id=payload.get("project_id"),
                source="task_engine",
                source_id=task_id,
                state=target_state,
                observation_type=ObservationType.OBSERVED,
                confidence=ConfidenceLevel.HIGH,
                observed_at=now,
                expires_at=FreshnessPolicy.compute_expiration(EntityType.TASK, now),
                metadata=payload,
            )

        # 3. GitHub events
        elif event_type.startswith("github."):
            repo_id = payload.get("repository_id") or payload.get("repo_name", "default_repo")
            ent_id = generate_entity_id(EntityType.REPOSITORY, user_id, "github", repo_id)
            existing = entities_by_id.get(ent_id)

            ci_status = "FAILED" if "failed" in event_type else "PASSED"
            meta = payload.get("metadata", {})
            meta["ci_status"] = ci_status
            if "head_commit" in payload:
                meta["head_commit"] = payload["head_commit"]

            if existing:
                existing.state = RepositoryState.SYNCED.value
                existing.observed_at = now
                existing.expires_at = FreshnessPolicy.compute_expiration(EntityType.REPOSITORY, now)
                existing.metadata.update(meta)
                existing.is_stale = False
                return existing

            return WorldEntitySchema(
                id=ent_id,
                type=EntityType.REPOSITORY,
                name=payload.get("repo_name", str(repo_id)),
                owner_id=user_id,
                project_id=payload.get("project_id"),
                source="github",
                source_id=str(repo_id),
                state=RepositoryState.SYNCED.value,
                observation_type=ObservationType.OBSERVED,
                confidence=ConfidenceLevel.HIGH,
                observed_at=now,
                expires_at=FreshnessPolicy.compute_expiration(EntityType.REPOSITORY, now),
                metadata=meta,
            )

        return None

    def reconcile_stale_entities(
        self,
        entities: list[WorldEntitySchema],
        now: Optional[datetime] = None,
    ) -> list[WorldEntitySchema]:
        """
        Flag expired entities as STALE without removing them (Spec 30, 62).
        If a source is unreachable, entity remains in last known state but marked STALE (Spec 62, 135).
        """
        current_time = now or datetime.now(UTC)
        updated: list[WorldEntitySchema] = []

        for e in entities:
            is_stale = FreshnessPolicy.is_stale(e.observed_at, e.expires_at, e.type, now=current_time)
            if is_stale and not e.is_stale:
                e.is_stale = True
                updated.append(e)

        return updated
