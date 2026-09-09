"""Tests for EventBus pub/sub, pattern routing, priority ordering, deduplication, and failure isolation."""

import pytest
import asyncio
from datetime import datetime, timezone

from app.events.bus import EventBus
from app.events.dedup import EventDeduplicator
from app.events.dispatcher import EventDispatcher
from app.events.schemas import Event


@pytest.fixture
def clean_bus():
    dedup = EventDeduplicator(window_seconds=10)
    dispatcher = EventDispatcher(deduplicator=dedup)
    bus = EventBus(deduplicator=dedup, dispatcher=dispatcher)
    return bus


@pytest.mark.asyncio
async def test_pattern_matching(clean_bus):
    exact_received = []
    wildcard_received = []
    global_received = []

    async def handle_exact(event):
        exact_received.append(event.event_id)

    async def handle_wildcard(event):
        wildcard_received.append(event.event_id)

    async def handle_global(event):
        global_received.append(event.event_id)

    clean_bus.subscribe("github.ci.failed", handle_exact, system_wide=True)
    clean_bus.subscribe("github.*", handle_wildcard, system_wide=True)
    clean_bus.subscribe("*", handle_global, system_wide=True)

    # 1. Matching github.ci.failed -> should match all 3
    event1 = clean_bus.publisher.create_event(
        event_type="github.ci.failed",
        source="github_webhook",
        payload={"repo": "kairo"},
    )
    await clean_bus.publish(event1, persist_log=False)

    assert len(exact_received) == 1
    assert len(wildcard_received) == 1
    assert len(global_received) == 1

    # 2. Matching github.pr.merged -> should match wildcard and global only
    event2 = clean_bus.publisher.create_event(
        event_type="github.pr.merged",
        source="github_webhook",
        payload={"pr_number": 42},
    )
    await clean_bus.publish(event2, persist_log=False)

    assert len(exact_received) == 1
    assert len(wildcard_received) == 2
    assert len(global_received) == 2

    # 3. Matching chat.message.created -> should match global only
    event3 = clean_bus.publisher.create_event(
        event_type="chat.message.created",
        source="chat_router",
        payload={"message": "hello"},
    )
    await clean_bus.publish(event3, persist_log=False)

    assert len(exact_received) == 1
    assert len(wildcard_received) == 2
    assert len(global_received) == 3


@pytest.mark.asyncio
async def test_subscriber_priority_ordering(clean_bus):
    call_order = []

    async def high_priority(event):
        call_order.append("high")

    async def low_priority(event):
        call_order.append("low")

    # Register low first, then high
    clean_bus.subscribe("test.priority", low_priority, priority=10, system_wide=True)
    clean_bus.subscribe("test.priority", high_priority, priority=100, system_wide=True)

    subscribers = clean_bus.get_subscribers()
    assert subscribers[0].priority == 100
    assert subscribers[1].priority == 10

    event = clean_bus.publisher.create_event(
        event_type="test.priority",
        source="test",
        payload={},
    )
    await clean_bus.publish(event, persist_log=False)

    assert call_order == ["high", "low"]


@pytest.mark.asyncio
async def test_failure_isolation_between_subscribers(clean_bus):
    """CRITICAL: An unhandled exception in one subscriber must never prevent other subscribers from executing."""
    healthy_ran = []

    async def failing_subscriber(event):
        raise RuntimeError("Network crashed inside notification dispatch!")

    async def healthy_subscriber(event):
        healthy_ran.append(event.event_id)

    clean_bus.subscribe("isolate.test", failing_subscriber, name="failing_sub", system_wide=True)
    clean_bus.subscribe("isolate.test", healthy_subscriber, name="healthy_sub", system_wide=True)

    event = clean_bus.publisher.create_event(
        event_type="isolate.test",
        source="test",
        payload={"data": "safe"},
    )

    # Publish should not raise; failure is isolated to failing_subscriber
    await clean_bus.publish(event, persist_log=False)

    assert len(healthy_ran) == 1
    assert healthy_ran[0] == event.event_id


@pytest.mark.asyncio
async def test_event_deduplication(clean_bus):
    delivered_count = 0

    async def counter(event):
        nonlocal delivered_count
        delivered_count += 1

    clean_bus.subscribe("dedup.test", counter, system_wide=True)

    event = clean_bus.publisher.create_event(
        event_type="dedup.test",
        source="test",
        payload={},
        metadata={"idempotency_key": "fixed_key_123"},
    )

    # First delivery
    await clean_bus.publish(event, persist_log=False)
    assert delivered_count == 1

    # Duplicate delivery with same event_id / idempotency_key
    await clean_bus.publish(event, persist_log=False)
    assert delivered_count == 1  # Deduplicated!
