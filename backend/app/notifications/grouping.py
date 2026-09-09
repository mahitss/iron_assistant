"""Notification grouping and event coalescing for Kairo Notifications (Task 34, Spec 46, 47, 98-100)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any
from pydantic import BaseModel, Field

from app.notifications.schemas import NotificationPriority, NotificationType

logger = logging.getLogger("kairo.notifications.grouping")


class GroupedNotificationBatch(BaseModel):
    group_key: str
    user_id: str
    project_id: str | None = None
    notification_type: NotificationType
    priority: NotificationPriority
    incident_id: str | None = None
    first_event_at: datetime
    last_event_at: datetime
    events_count: int = 1
    sample_titles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationGrouper:
    """
    Coalesces rapid repeated events into meaningful grouped summaries.
    Example: 5 CI check failures -> "5 CI failures in Kairo".
    Urgent security notifications bypass grouping and deliver immediately (Spec 47).
    """

    def __init__(self, grouping_window_seconds: int = 60) -> None:
        self.grouping_window_seconds = grouping_window_seconds
        # In-memory active grouping batches: group_key -> GroupedNotificationBatch
        self._active_batches: dict[str, GroupedNotificationBatch] = {}

    @classmethod
    def compute_group_key(
        cls,
        user_id: str,
        event_type: str,
        project_id: str | None = None,
        incident_id: str | None = None,
    ) -> str:
        """Calculate logical grouping key."""
        if incident_id:
            return f"group:incident:{user_id}:{incident_id}"
        prefix = event_type.split(".")[0] if "." in event_type else event_type
        proj = project_id or "global"
        return f"group:{user_id}:{proj}:{prefix}"

    def can_group(self, event_type: str, priority: NotificationPriority) -> bool:
        """Determine if an event is eligible for grouping. URGENT and APPROVAL events bypass grouping."""
        if priority == NotificationPriority.URGENT:
            return False
        if event_type.startswith("approval."):
            return False
        # High-volume groupable categories: CI, task steps, system degradation
        groupable_namespaces = ("github.ci", "task.step", "workflow.step", "system.degradation")
        return any(event_type.startswith(p) for p in groupable_namespaces)

    def record_event(
        self,
        user_id: str,
        event_type: str,
        title: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
        project_id: str | None = None,
        incident_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, GroupedNotificationBatch | None]:
        """
        Record an incoming event into a grouping window.
        Returns:
            (should_hold, batch): If True, do not create an individual notification yet.
        """
        if not self.can_group(event_type, priority):
            return False, None

        key = self.compute_group_key(user_id, event_type, project_id, incident_id)
        now = datetime.now(UTC)

        batch = self._active_batches.get(key)
        if batch:
            # Check if still within window
            window_limit = batch.first_event_at + timedelta(seconds=self.grouping_window_seconds)
            if now <= window_limit:
                batch.events_count += 1
                batch.last_event_at = now
                if len(batch.sample_titles) < 3:
                    batch.sample_titles.append(title)
                logger.info("Coalesced event into group '%s' (total: %d)", key, batch.events_count)
                return True, batch
            else:
                # Window expired, release batch
                del self._active_batches[key]

        # Start a new batch
        new_batch = GroupedNotificationBatch(
            group_key=key,
            user_id=user_id,
            project_id=project_id,
            notification_type=notification_type,
            priority=priority,
            incident_id=incident_id,
            first_event_at=now,
            last_event_at=now,
            events_count=1,
            sample_titles=[title],
            metadata=metadata or {},
        )
        self._active_batches[key] = new_batch
        return False, new_batch

    def format_grouped_notification(self, batch: GroupedNotificationBatch) -> tuple[str, str]:
        """Generate human-readable summary for a coalesced batch."""
        if batch.incident_id:
            title = f"Incident Alert: {batch.events_count} related events recorded"
            body = f"{batch.events_count} events grouped under incident '{batch.incident_id}'."
        elif batch.notification_type == NotificationType.TASK:
            title = f"{batch.events_count} task updates in {batch.project_id or 'workspace'}"
            body = f"Kairo recorded {batch.events_count} task execution events."
        else:
            title = f"{batch.events_count} CI / build events in {batch.project_id or 'workspace'}"
            body = f"Multiple build check events reported: {', '.join(batch.sample_titles)}."

        return title, body
