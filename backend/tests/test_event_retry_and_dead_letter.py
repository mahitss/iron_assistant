"""Tests for retry policies, error classification, dead letter capturing, and replay safety."""

import pytest
import asyncio
from datetime import datetime, timezone

from app.events.bus import EventBus
from app.events.dead_letter import DeadLetterManager
from app.events.dedup import EventDeduplicator
from app.events.dispatcher import EventDispatcher
from app.events.retry import (
    RetryPolicy,
    TransientDeliveryError,
    PermanentDeliveryError,
)
from app.events.schemas import Event, ReplaySafety
from app.events.registry import event_registry, EventRegistration, EventSecurityClass


@pytest.mark.asyncio
async def test_retry_on_transient_error():
    attempts = 0

    async def flaky_handler(event):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TransientDeliveryError("Temporary connection timeout")
        return "success"

    policy = RetryPolicy(max_retries=3, initial_backoff=0.01, max_backoff=0.05, jitter=False)
    result = await policy.execute_with_retry(flaky_handler, Event(
        event_id="e1", event_type="test.event", event_version="1", timestamp=datetime.now(timezone.utc), source="test"
    ))
    assert result == "success"
    assert attempts == 3


@pytest.mark.asyncio
async def test_fast_fail_on_permanent_error():
    attempts = 0

    async def invalid_handler(event):
        nonlocal attempts
        attempts += 1
        raise ValueError("Invalid payload schema: missing required field")

    policy = RetryPolicy(max_retries=3, initial_backoff=0.01)
    with pytest.raises(PermanentDeliveryError):
        await policy.execute_with_retry(invalid_handler, Event(
            event_id="e2", event_type="test.event", event_version="1", timestamp=datetime.now(timezone.utc), source="test"
        ))
    # Must fail immediately on first attempt without retrying!
    assert attempts == 1


@pytest.mark.asyncio
async def test_dead_letter_recording_and_trace_sanitization():
    dl_manager = DeadLetterManager()
    event = Event(
        event_id="evt_dl_test",
        event_type="test.event",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="unit_test",
        payload={"secret_token": "ghp_SECRET_TOKEN_XYZ", "user": "alice"},
    )

    try:
        raise ValueError("Failed with key sk-ant-secret123456789")
    except Exception as exc:
        dl_id = await dl_manager.record_failure(
            event=event,
            subscriber_name="test_subscriber",
            error=exc,
            retry_count=3,
        )

    record = await dl_manager.get_dead_letter(dl_id)
    assert record is not None
    assert record["id"] == dl_id
    assert record["status"] == "UNRESOLVED"
    assert record["subscriber_name"] == "test_subscriber"
    # Zero secret leakage: verify payload was sanitized in dead letter
    assert record["event_payload"]["secret_token"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_dead_letter_strict_replay_guard():
    """CRITICAL: Non-replayable events must raise PermissionError on replay attempt."""
    dl_manager = DeadLetterManager()
    bus = EventBus()

    # 1. Non-replayable event (e.g. computer.action.requested or device.revoked)
    event_nr = Event(
        event_id="evt_nr_1",
        event_type="computer.action.requested",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="unit_test",
        payload={"action": "click"},
    )
    dl_id_nr = await dl_manager.record_failure(
        event=event_nr,
        subscriber_name="os_subscriber",
        error=RuntimeError("Desktop agent unavailable"),
    )

    # Replay MUST be rejected
    with pytest.raises(PermissionError) as exc_info:
        await dl_manager.replay_dead_letter(dl_id_nr, event_bus=bus, force=True)
    assert "NON_REPLAYABLE" in str(exc_info.value)

    # 2. Replay-safe event (e.g. notification.read)
    event_safe = Event(
        event_id="evt_safe_1",
        event_type="notification.read",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="unit_test",
        payload={"notification_id": "notif_99"},
    )
    dl_id_safe = await dl_manager.record_failure(
        event=event_safe,
        subscriber_name="notif_subscriber",
        error=ConnectionError("Redis temporary glitch"),
    )

    replayed = await dl_manager.replay_dead_letter(dl_id_safe, event_bus=bus)
    assert replayed is True
    updated = await dl_manager.get_dead_letter(dl_id_safe)
    assert updated["status"] == "REPLAYED"


@pytest.mark.asyncio
async def test_dead_letter_discard():
    dl_manager = DeadLetterManager()
    event = Event(
        event_id="evt_discard_1",
        event_type="chat.message.created",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="unit_test",
    )
    dl_id = await dl_manager.record_failure(
        event=event,
        subscriber_name="test_sub",
        error=RuntimeError("Test error"),
    )
    discarded = await dl_manager.discard_dead_letter(dl_id, reason="Obsolete event")
    assert discarded is True
    record = await dl_manager.get_dead_letter(dl_id)
    assert record["status"] == "DISCARDED"
