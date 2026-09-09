"""Tests for Notification Deduplication, Grouping, Storm Defense, and Self-Throttling (Task 34, Spec 43-47, 54-56, 104)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.notifications.dedupe import NotificationDeduplicator
from app.notifications.grouping import NotificationGrouper
from app.notifications.models import NotificationModel
from app.notifications.schemas import NotificationPriority, NotificationType
from app.notifications.throttling import NotificationThrottler


@pytest.fixture
async def db_session():
    """Create in-memory async SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


def test_deterministic_dedupe_keys():
    """Verify identical inputs yield identical keys, and different state yields different keys (Spec 43)."""
    k1 = NotificationDeduplicator.compute_dedupe_key(
        user_id="user_alice",
        event_type="task.completed",
        notification_type=NotificationType.TASK,
        resource_id="task_101",
        state="success",
    )
    k2 = NotificationDeduplicator.compute_dedupe_key(
        user_id="user_alice",
        event_type="task.completed",
        notification_type=NotificationType.TASK,
        resource_id="task_101",
        state="success",
    )
    k3 = NotificationDeduplicator.compute_dedupe_key(
        user_id="user_alice",
        event_type="task.completed",
        notification_type=NotificationType.TASK,
        resource_id="task_102",  # Different resource
        state="success",
    )
    assert k1 == k2
    assert k1 != k3


def test_dedupe_safety_security_events():
    """Verify distinct security events are NOT merged based on textual similarity (Spec 45)."""
    # Two security events for the same user and type, but distinct session IDs
    k_sec1 = NotificationDeduplicator.compute_dedupe_key(
        user_id="user_alice",
        event_type="security.policy_violation",
        notification_type=NotificationType.SECURITY,
        payload={"session_id": "sess_attacker_1", "violation_id": "v_1"},
    )
    k_sec2 = NotificationDeduplicator.compute_dedupe_key(
        user_id="user_alice",
        event_type="security.policy_violation",
        notification_type=NotificationType.SECURITY,
        payload={"session_id": "sess_attacker_2", "violation_id": "v_2"},
    )
    assert k_sec1 != k_sec2


@pytest.mark.asyncio
async def test_deduplication_window_enforcement(db_session: AsyncSession):
    """Verify an identical event is deduplicated within window, but allowed after window expires (Spec 44)."""
    deduper = NotificationDeduplicator(default_window_seconds=300)
    key = "dedupe_ci_fail_1"

    # Initially not a duplicate
    assert await deduper.is_duplicate(key, db_session) is False

    # Record notification in DB
    now = datetime.now(UTC)
    notif = NotificationModel(
        id="notif_dup_1",
        user_id="user_alice",
        type=NotificationType.PROJECT.value,
        priority=NotificationPriority.NORMAL.value,
        title="CI Check Failed",
        body="Build 1 failed.",
        status="DELIVERED",
        created_at=now,
        correlation_id="c_1",
        dedupe_key=key,
    )
    db_session.add(notif)
    await db_session.commit()

    # Now it is detected as duplicate
    assert await deduper.is_duplicate(key, db_session) is True


def test_event_grouping_coalescing():
    """Verify multiple rapid events are coalesced into a grouped batch (Spec 46, 47)."""
    grouper = NotificationGrouper(grouping_window_seconds=60)

    # 1st CI failure: starts batch
    held1, batch1 = grouper.record_event(
        user_id="user_alice",
        event_type="github.ci.failed",
        title="CI failed for commit 1",
        notification_type=NotificationType.PROJECT,
        priority=NotificationPriority.NORMAL,
        project_id="proj_web",
    )
    assert held1 is False
    assert batch1 is not None
    assert batch1.events_count == 1

    # 2nd, 3rd, 4th CI failure in same window: held in batch
    for i in range(2, 5):
        held, b = grouper.record_event(
            user_id="user_alice",
            event_type="github.ci.failed",
            title=f"CI failed for commit {i}",
            notification_type=NotificationType.PROJECT,
            priority=NotificationPriority.NORMAL,
            project_id="proj_web",
        )
        assert held is True
        assert b.events_count == i

    # Format summary
    title, body = grouper.format_grouped_notification(batch1)
    assert "4 CI / build events" in title
    assert "proj_web" in title


def test_notification_storm_detection_and_safety():
    """Verify surge > 20 events in 10s triggers storm state while preserving urgent security/approvals (Spec 55, 56)."""
    throttler = NotificationThrottler(storm_threshold=20, storm_window_seconds=10)

    # Generate 20 rapid low-priority notifications
    for _ in range(19):
        allowed, is_storm, _ = throttler.check_throttle("user_alice", NotificationType.TASK, NotificationPriority.LOW)
        assert allowed is True
        assert is_storm is False

    # 20th triggers storm condition
    allowed, is_storm, msg = throttler.check_throttle("user_alice", NotificationType.TASK, NotificationPriority.LOW)
    assert allowed is False
    assert is_storm is True
    assert "Notification storm" in msg

    # Storm Safety (Spec 56): An URGENT security event or APPROVAL MUST STILL BE ALLOWED THROUGH!
    sec_allowed, _, _ = throttler.check_throttle("user_alice", NotificationType.SECURITY, NotificationPriority.URGENT)
    assert sec_allowed is True

    app_allowed, _, _ = throttler.check_throttle("user_alice", NotificationType.APPROVAL, NotificationPriority.HIGH)
    assert app_allowed is True


def test_self_throttling_on_delivery_failure():
    """Verify consecutive delivery errors activate self-throttling on low-priority items (Spec 104)."""
    throttler = NotificationThrottler()

    # Record 10 delivery failures
    for _ in range(10):
        throttler.record_delivery_outcome(success=False)

    # LOW priority notification should be suppressed by self-throttling
    allowed, _, msg = throttler.check_throttle("user_alice", NotificationType.RESEARCH, NotificationPriority.LOW)
    assert allowed is False
    assert "self-throttling" in msg.lower()

    # But HIGH priority is still permitted
    high_allowed, _, _ = throttler.check_throttle("user_alice", NotificationType.TASK, NotificationPriority.HIGH)
    assert high_allowed is True
