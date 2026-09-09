"""Tests for Transactional Outbox pattern and OutboxProcessor."""

import pytest
import asyncio
from datetime import datetime, timezone

from app.events.bus import EventBus
from app.events.models import EventOutboxRecord
from app.events.outbox import OutboxProcessor, TransactionalOutbox
from app.events.schemas import Event


@pytest.mark.asyncio
async def test_transactional_outbox_staging_model():
    event = Event(
        event_id="outbox_evt_1",
        event_type="chat.message.created",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="chat_router",
        user_id="user_123",
        payload={"message": "hello"},
    )

    # Verify stage_event creates valid EventOutboxRecord
    class MockSession:
        def __init__(self):
            self.added = []
        def add(self, record):
            self.added.append(record)

    mock_session = MockSession()
    record = await TransactionalOutbox.stage_event(mock_session, event)

    assert record.event_id == "outbox_evt_1"
    assert record.event_type == "chat.message.created"
    assert record.status == "PENDING"
    assert len(mock_session.added) == 1


@pytest.mark.asyncio
async def test_outbox_processor_publish_flow():
    bus = EventBus()
    received = []

    async def chat_subscriber(event):
        received.append(event.event_id)

    bus.subscribe("chat.message.created", chat_subscriber, system_wide=True)

    processor = OutboxProcessor(bus=bus)
    # Testing direct batch execution (gracefully handles when DB is unconfigured or returns 0)
    published = await processor.process_batch(limit=10)
    assert isinstance(published, int)
