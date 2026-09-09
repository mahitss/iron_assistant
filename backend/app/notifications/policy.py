from datetime import datetime
from enum import Enum
import logging
from typing import Any

from app.events.schemas import Event
from app.notifications.models import NotificationPreferenceModel
from app.notifications.preferences import NotificationPreferencesManager
from app.notifications.priority import PriorityResolver
from app.notifications.schemas import NotificationPriority, NotificationType

logger = logging.getLogger("kairo.notifications.policy")


class DeliveryDecision(str, Enum):
    """Authoritative routing decision produced by NotificationPolicy."""

    DELIVER_IMMEDIATE = "DELIVER_IMMEDIATE"
    GROUP = "GROUP"
    DIGEST = "DIGEST"
    SUPPRESS = "SUPPRESS"


class NotificationPolicy:
    """
    Evaluates whether an incoming event or candidate should become a notification,
    and if so, how it should be delivered (immediate, grouped, digested, or suppressed).
    """

    # Low-level noisy events to strictly filter out (Spec 96)
    IGNORED_EVENT_PATTERNS = (
        "tool.started",
        "tool.completed",
        "chat.request.started",
        "chat.response.started",
        "memory.extracted",
        "evaluation.step",
        "presence.heartbeat",
        "multimodal.processing",
        "world.observation",
    )

    @classmethod
    def should_ignore_event(cls, event_type: str) -> bool:
        """Filter out noisy, internal operational events (Spec 96)."""
        if any(event_type.startswith(p) or event_type == p for p in cls.IGNORED_EVENT_PATTERNS):
            return True
        return False

    @classmethod
    def map_event_to_notification_type(cls, event_type: str) -> NotificationType:
        """Map canonical event namespace to notification type."""
        prefix = event_type.split(".")[0] if "." in event_type else event_type
        if prefix == "approval":
            return NotificationType.APPROVAL
        if prefix == "security":
            return NotificationType.SECURITY
        if prefix in ("device", "companion"):
            return NotificationType.DEVICE
        if prefix in ("task",):
            return NotificationType.TASK
        if prefix in ("workflow", "automation"):
            return NotificationType.AUTOMATION
        if prefix in ("github", "project"):
            return NotificationType.PROJECT
        if prefix in ("research",):
            return NotificationType.RESEARCH
        if prefix in ("system",):
            return NotificationType.SYSTEM
        return NotificationType.TASK

    @classmethod
    def evaluate(
        cls,
        event: Event,
        preferences: NotificationPreferenceModel,
        is_duplicate: bool,
        is_rate_limited: bool,
        is_storm: bool,
        now_dt: datetime | None = None,
    ) -> tuple[DeliveryDecision, NotificationType, NotificationPriority, str | None]:
        """
        Evaluate full notification policy for an event.
        Returns:
            (decision, notification_type, priority, reason)
        """
        event_type = event.event_type

        # 1. Check event noise filter (Spec 96)
        if cls.should_ignore_event(event_type):
            return DeliveryDecision.SUPPRESS, NotificationType.TASK, NotificationPriority.LOW, "Low-level event ignored"

        # 2. Determine type & priority
        notif_type = cls.map_event_to_notification_type(event_type)
        payload = event.payload if isinstance(event.payload, dict) else {}
        priority = PriorityResolver.resolve_priority(event_type, notif_type, payload)

        # 3. Deduplication check (Spec 43)
        if is_duplicate:
            return DeliveryDecision.SUPPRESS, notif_type, priority, "Duplicate notification suppressed"

        # 4. Storm defense (Spec 55, 56)
        if is_storm and priority not in (NotificationPriority.HIGH, NotificationPriority.URGENT):
            return DeliveryDecision.GROUP, notif_type, priority, "Notification storm active; grouping event"

        # 5. Rate limit check (Spec 54)
        if is_rate_limited and priority not in (NotificationPriority.HIGH, NotificationPriority.URGENT):
            return DeliveryDecision.SUPPRESS, notif_type, priority, "Rate limit exceeded; non-critical event dropped"

        # 6. User type preference check
        type_prefs = preferences.type_preferences or {}
        if notif_type.value in type_prefs and not type_prefs[notif_type.value]:
            # User opted out of this type (except mandatory security)
            if notif_type != NotificationType.SECURITY:
                return DeliveryDecision.SUPPRESS, notif_type, priority, f"User opted out of {notif_type.value}"

        # 7. Priority threshold check
        min_prio = preferences.min_priority or NotificationPriority.LOW.value
        prio_order = {
            NotificationPriority.LOW.value: 1,
            NotificationPriority.NORMAL.value: 2,
            NotificationPriority.HIGH.value: 3,
            NotificationPriority.URGENT.value: 4,
        }
        if prio_order.get(priority.value, 1) < prio_order.get(min_prio, 1) and notif_type != NotificationType.SECURITY:
            return DeliveryDecision.SUPPRESS, notif_type, priority, f"Priority below user threshold {min_prio}"

        # 8. Quiet hours check (Spec 49, 50)
        if NotificationPreferencesManager.is_in_quiet_hours(preferences, now_dt=now_dt):
            if not NotificationPreferencesManager.should_deliver_during_quiet_hours(notif_type, priority):
                if preferences.digest_enabled:
                    return DeliveryDecision.DIGEST, notif_type, priority, "Quiet hours active; queued for digest"
                return DeliveryDecision.SUPPRESS, notif_type, priority, "Quiet hours active; suppressed"

        return DeliveryDecision.DELIVER_IMMEDIATE, notif_type, priority, "Policy approved immediate delivery"
