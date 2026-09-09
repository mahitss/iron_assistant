"""Tests for command protocol validation, TTL expiration, idempotency, and session lifecycle."""

import time

import pytest

from companion.src.transport.client import CompanionTransportClient, SessionState
from companion.src.transport.protocol import CommandProtocolValidator


def test_protocol_validation_success():
    """Verify valid command frame passes verification."""
    validator = CommandProtocolValidator(ttl_seconds=30.0)
    cmd = {
        "command_id": "cmd_valid_1",
        "device_id": "dev_test_42",
        "action": "screen.capture",
        "parameters": {},
        "timestamp": time.time(),
    }
    res = validator.validate_command(cmd, target_device_id="dev_test_42")
    assert res["command_id"] == "cmd_valid_1"
    assert res["action"] == "screen.capture"


def test_protocol_device_mismatch():
    """Verify command intended for another device is rejected."""
    validator = CommandProtocolValidator()
    cmd = {
        "command_id": "cmd_mismatch_1",
        "device_id": "dev_wrong_device",
        "action": "screen.capture",
    }
    with pytest.raises(PermissionError):
        validator.validate_command(cmd, target_device_id="dev_correct_device")


def test_protocol_idempotency_deduplication():
    """Verify duplicate command_id is rejected."""
    validator = CommandProtocolValidator()
    cmd = {
        "command_id": "cmd_dup_1",
        "device_id": "dev_test_42",
        "action": "mouse.click",
    }
    validator.validate_command(cmd, target_device_id="dev_test_42")

    # Duplicate submission
    with pytest.raises(ValueError, match="Duplicate command rejected"):
        validator.validate_command(cmd, target_device_id="dev_test_42")


def test_protocol_ttl_expiration():
    """Verify command older than 30s TTL is rejected."""
    validator = CommandProtocolValidator(ttl_seconds=30.0)
    stale_time = time.time() - 45.0  # 45 seconds old
    cmd = {
        "command_id": "cmd_stale_1",
        "device_id": "dev_test_42",
        "action": "mouse.click",
        "timestamp": stale_time,
    }
    with pytest.raises(TimeoutError, match="expired"):
        validator.validate_command(cmd, target_device_id="dev_test_42")


def test_transport_offline_queue_clearing():
    """Verify transport client clears pending commands when disconnected."""
    client = CompanionTransportClient()
    assert client.session_state == SessionState.DISCONNECTED

    # Cannot enqueue when disconnected
    with pytest.raises(ConnectionError):
        client.enqueue_command({"command_id": "cmd_1"})

    # Manually simulate connected state
    client._session_state = SessionState.CONNECTED
    client.enqueue_command({"command_id": "cmd_1"})
    client.enqueue_command({"command_id": "cmd_2"})

    # Disconnect
    client.handle_disconnect("Network dropped")
    assert client.session_state == SessionState.DISCONNECTED
    assert client.get_next_command() is None
