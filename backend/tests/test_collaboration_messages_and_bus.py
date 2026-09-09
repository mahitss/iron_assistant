"""Tests for Scoped Agent Messaging, Hash Deduplication, and Priority (Task 44)."""

import pytest
from app.agents.messages import (
    AgentMessage,
    DuplicateMessageError,
    MessageAuthorizationError,
    MessageBus,
    MessageType,
)


def test_agent_message_creation_and_delivery():
    bus = MessageBus()
    msg = AgentMessage(
        message_id="msg_001",
        sender="agent_coder",
        recipient="agent_reviewer",
        type=MessageType.REVIEW,
        payload={"diff": "+ def test(): pass"},
        contract_id="ct_100",
        priority=1,
    )

    bus.send(msg)
    pending = bus.get_messages("agent_reviewer")
    assert len(pending) == 1
    assert pending[0].message_id == "msg_001"
    assert pending[0].type == MessageType.REVIEW


def test_message_deduplication():
    """Duplicate messages with identical payload, sender, and contract are safely discarded or flagged."""
    bus = MessageBus()
    msg1 = AgentMessage(
        message_id="msg_a",
        sender="agent_researcher",
        recipient="agent_analyst",
        type=MessageType.EVIDENCE,
        payload={"fact": "Port 443 is open"},
        contract_id="ct_200",
    )
    bus.send(msg1)

    # Identical message sent again
    msg2 = AgentMessage(
        message_id="msg_b",
        sender="agent_researcher",
        recipient="agent_analyst",
        type=MessageType.EVIDENCE,
        payload={"fact": "Port 443 is open"},
        contract_id="ct_200",
    )

    # Bus deduplicates without creating redundant queue entries
    duplicate_result = bus.send(msg2)
    assert duplicate_result is False
    assert len(bus.get_messages("agent_analyst")) == 1


def test_message_priority_ordering():
    """High priority messages are delivered before normal messages."""
    bus = MessageBus()

    low_msg = AgentMessage(
        message_id="msg_low",
        sender="agent_1",
        recipient="supervisor",
        type=MessageType.HEARTBEAT,
        payload={"status": "ok"},
        contract_id="ct_1",
        priority=0,
    )
    bus.send(low_msg)

    high_msg = AgentMessage(
        message_id="msg_high",
        sender="agent_1",
        recipient="supervisor",
        type=MessageType.WARNING,
        payload={"alert": "Resource near exhaustion"},
        contract_id="ct_1",
        priority=10,
    )
    bus.send(high_msg)

    messages = bus.get_messages("supervisor")
    assert len(messages) == 2
    assert messages[0].message_id == "msg_high"
    assert messages[1].message_id == "msg_low"


def test_message_authorization_scope():
    """Agents can only send messages within authorized collaboration contracts."""
    bus = MessageBus()
    bus.register_authorized_contract("ct_authorized", ["agent_a", "agent_b"])

    unauth_msg = AgentMessage(
        message_id="msg_unauth",
        sender="agent_external",
        recipient="agent_b",
        type=MessageType.TASK,
        payload={"cmd": "leak_data"},
        contract_id="ct_authorized",
    )

    with pytest.raises(MessageAuthorizationError):
        bus.send_authenticated(unauth_msg)
