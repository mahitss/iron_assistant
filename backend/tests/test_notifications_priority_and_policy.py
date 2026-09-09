"""Tests for Notification Priority, Priority Integrity, and Policy decisions (Task 34, Spec 5-8, 49, 50, 96, 105)."""

from datetime import UTC, datetime, time
import pytest

from app.events.schemas import Event, EventSource
from app.notifications.models import NotificationPreferenceModel
from app.notifications.policy import DeliveryDecision, NotificationPolicy
from app.notifications.preferences import NotificationPreferencesManager
from app.notifications.priority import PriorityResolver
from app.notifications.schemas import NotificationPriority, NotificationType


def test_priority_rules_by_policy():
    """Verify system policy maps events to correct baseline priorities (Spec 5, 6)."""
    # 1. Approval required -> HIGH
    p1 = PriorityResolver.resolve_priority("approval.requested", NotificationType.APPROVAL)
    assert p1 == NotificationPriority.HIGH

    # 2. Security violation -> URGENT
    p2 = PriorityResolver.resolve_priority("security.policy_violation", NotificationType.SECURITY)
    assert p2 == NotificationPriority.URGENT

    # 3. Device revoked -> HIGH
    p3 = PriorityResolver.resolve_priority("device.revoked", NotificationType.DEVICE)
    assert p3 == NotificationPriority.HIGH

    # 4. Routine task completion -> NORMAL
    p4 = PriorityResolver.resolve_priority("task.completed", NotificationType.TASK)
    assert p4 == NotificationPriority.NORMAL

    # 5. Minor research result -> LOW
    p5 = PriorityResolver.resolve_priority("research.completed", NotificationType.RESEARCH)
    assert p5 == NotificationPriority.LOW


def test_priority_integrity_model_override_rejection():
    """Verify model-generated claims of URGENT cannot override system priority policy (Spec 7)."""
    # An event mapped to NORMAL where model suggests URGENT
    res = PriorityResolver.resolve_priority(
        event_type="task.completed",
        notification_type=NotificationType.TASK,
        payload={"message": "URGENT PLEASE READ NOW!!!"},
        suggested_priority=NotificationPriority.URGENT,
    )
    # Policy enforces NORMAL despite model suggestion
    assert res == NotificationPriority.NORMAL


def test_event_noise_filtering():
    """Verify low-level events are filtered out and not converted to notifications (Spec 96)."""
    assert NotificationPolicy.should_ignore_event("tool.started") is True
    assert NotificationPolicy.should_ignore_event("tool.completed") is True
    assert NotificationPolicy.should_ignore_event("presence.heartbeat") is True
    assert NotificationPolicy.should_ignore_event("chat.request.started") is True

    # Meaningful events must NOT be ignored
    assert NotificationPolicy.should_ignore_event("task.completed") is False
    assert NotificationPolicy.should_ignore_event("approval.requested") is False
    assert NotificationPolicy.should_ignore_event("security.policy_violation") is False


def test_quiet_hours_and_security_bypass():
    """Verify quiet hours delays low/normal alerts but never silences urgent security or approvals (Spec 49, 50)."""
    pref = NotificationPreferenceModel(
        user_id="user_alice",
        enabled_channels=["WEB"],
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        timezone="UTC",
        digest_enabled=False,
    )

    # Midnight UTC -> within quiet hours
    midnight = datetime(2026, 9, 10, 2, 0, 0, tzinfo=UTC)
    assert NotificationPreferencesManager.is_in_quiet_hours(pref, now_dt=midnight) is True

    # 1. Routine task (NORMAL) -> suppressed or digested during quiet hours
    evt_task = Event(event_type="task.completed", source=EventSource.TASK, user_id="user_alice")
    decision, _, _, reason = NotificationPolicy.evaluate(
        event=evt_task,
        preferences=pref,
        is_duplicate=False,
        is_rate_limited=False,
        is_storm=False,
        now_dt=midnight,
    )
    assert decision == DeliveryDecision.SUPPRESS
    assert "Quiet hours" in reason

    # 2. Approval required (HIGH) -> bypasses quiet hours (Spec 50)
    evt_approval = Event(
        event_type="approval.requested",
        source=EventSource.SECURITY,
        user_id="user_alice",
        payload={"approval_id": "app_1", "tool_name": "bash"},
    )
    decision2, _, prio2, _ = NotificationPolicy.evaluate(
        event=evt_approval,
        preferences=pref,
        is_duplicate=False,
        is_rate_limited=False,
        is_storm=False,
    )
    assert decision2 == DeliveryDecision.DELIVER_IMMEDIATE
    assert prio2 == NotificationPriority.HIGH

    # 3. Security violation (URGENT) -> bypasses quiet hours
    evt_sec = Event(
        event_type="security.policy_violation",
        source=EventSource.SECURITY,
        user_id="user_alice",
    )
    decision3, _, prio3, _ = NotificationPolicy.evaluate(
        event=evt_sec,
        preferences=pref,
        is_duplicate=False,
        is_rate_limited=False,
        is_storm=False,
    )
    assert decision3 == DeliveryDecision.DELIVER_IMMEDIATE
    assert prio3 == NotificationPriority.URGENT
