"""Policy-driven priority escalation and escalation channel routing (Task 34, Spec 101, 102)."""

import logging
from typing import Any

from app.notifications.schemas import ChannelType, NotificationPriority

logger = logging.getLogger("kairo.notifications.escalation")


class PriorityEscalationPolicy:
    """
    Evaluates whether an unresolved event or incident qualifies for priority escalation.
    Invariant (Spec 101): Escalates strictly through policy steps (LOW -> NORMAL -> HIGH) and never indefinitely.
    """

    ESCALATION_LADDER = {
        NotificationPriority.LOW: NotificationPriority.NORMAL,
        NotificationPriority.NORMAL: NotificationPriority.HIGH,
        NotificationPriority.HIGH: NotificationPriority.URGENT,
        NotificationPriority.URGENT: NotificationPriority.URGENT,  # Ceiling
    }

    @classmethod
    def escalate_priority(cls, current_priority: NotificationPriority, persistence_count: int) -> NotificationPriority:
        """
        Escalate priority if failure persists across multiple occurrences.
        Requires at least 3 occurrences to step up one level.
        """
        if persistence_count < 3:
            return current_priority

        new_priority = cls.ESCALATION_LADDER.get(current_priority, current_priority)
        if new_priority != current_priority:
            logger.info("Policy escalated priority from '%s' to '%s' (persisted %d times).", current_priority.value, new_priority.value, persistence_count)
        return new_priority

    @classmethod
    def resolve_escalation_channels(
        cls,
        priority: NotificationPriority,
        base_channels: list[ChannelType],
    ) -> list[ChannelType]:
        """
        Determine if higher-tier channels should be engaged for unresolved HIGH/URGENT alerts.
        """
        channels = list(base_channels)
        if priority in (NotificationPriority.HIGH, NotificationPriority.URGENT):
            if ChannelType.DESKTOP not in channels:
                channels.append(ChannelType.DESKTOP)
        return channels
