"""Tests for Event Bus security authority enforcement, zero secret leakage, and tenant isolation."""

import pytest
import asyncio
from datetime import datetime, timezone

from app.events.bus import EventBus
from app.events.safety import EventSecurityGuard
from app.events.schemas import Event


@pytest.mark.asyncio
async def test_forgery_defense_blocks_untrusted_sources():
    """CRITICAL: Model outputs or untrusted sources can NEVER publish privileged security events."""
    bus = EventBus()

    # 1. Untrusted source attempting to emit 'security.allowed'
    forged_sec_event = Event(
        event_id="forged_1",
        event_type="security.allowed",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="model_output",  # Untrusted!
        payload={"action": "delete_database"},
    )
    with pytest.raises(PermissionError) as exc_info:
        await bus.publish(forged_sec_event, persist_log=False)
    assert "attempted to publish privileged event" in str(exc_info.value)

    # 2. Untrusted source attempting to emit 'approval.granted'
    forged_app_event = Event(
        event_id="forged_2",
        event_type="approval.granted",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="chat_user",  # Untrusted!
        payload={"action": "transfer_funds"},
    )
    with pytest.raises(PermissionError) as exc_info:
        await bus.publish(forged_app_event, persist_log=False)
    assert "attempted to publish privileged event" in str(exc_info.value)

    # 3. Authorized source 'security_center' succeeds
    valid_sec_event = Event(
        event_id="valid_1",
        event_type="security.allowed",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source="security_center",  # Authorized!
        payload={"action": "read_file"},
    )
    res = await bus.publish(valid_sec_event, persist_log=False)
    assert res.event_id == "valid_1"


def test_zero_secret_leakage_payload_sanitization():
    """Verify that credentials, tokens, and API keys are redacted before publication."""
    raw_payload = {
        "api_key": "sk-ant-api03-abcdef1234567890",
        "nested": {
            "password": "super_secret_password_123",
            "token": "ghp_PersonalAccessTokenABCDEF",
        },
        "safe_data": "Public information",
    }

    sanitized = EventSecurityGuard.sanitize_payload(raw_payload)

    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["safe_data"] == "Public information"


@pytest.mark.asyncio
async def test_tenant_and_user_isolation():
    """CRITICAL: A subscriber for User A must never receive User B's events."""
    bus = EventBus()
    user_a_received = []
    user_b_received = []
    system_wide_received = []

    async def sub_user_a(event):
        user_a_received.append(event.event_id)

    async def sub_user_b(event):
        user_b_received.append(event.event_id)

    async def sub_audit(event):
        system_wide_received.append(event.event_id)

    # Register tenant-scoped subscribers
    bus.subscribe("chat.*", sub_user_a, name="sub_a", allowed_user_ids={"user_A"}, system_wide=False)
    bus.subscribe("chat.*", sub_user_b, name="sub_b", allowed_user_ids={"user_B"}, system_wide=False)
    bus.subscribe("chat.*", sub_audit, name="sub_audit", system_wide=True)

    # Event for User A
    event_a = bus.publisher.create_event(
        event_type="chat.message.created",
        source="chat",
        payload={"msg": "from A"},
        user_id="user_A",
    )
    await bus.publish(event_a, persist_log=False)

    assert event_a.event_id in user_a_received
    assert event_a.event_id not in user_b_received
    assert event_a.event_id in system_wide_received

    # Event for User B
    event_b = bus.publisher.create_event(
        event_type="chat.message.created",
        source="chat",
        payload={"msg": "from B"},
        user_id="user_B",
    )
    await bus.publish(event_b, persist_log=False)

    assert event_b.event_id in user_b_received
    assert event_b.event_id not in user_a_received
    assert event_b.event_id in system_wide_received
