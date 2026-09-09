"""Unit tests for communication channels, authorizations, rate limits, quiet hours, and message normalization."""

from datetime import datetime, time
import pytest

from app.communication.channels import (
    ChannelAuthorizationError,
    ChannelManager,
    QuietHoursViolationError,
    RateLimitExceededError,
)
from app.communication.messages import MessageNormalizer
from app.communication.schemas import (
    CommunicationChannel,
    CommunicationUrgency,
    MessageDirection,
    MessageStatus,
    PrivacyScope,
    RecipientSchema,
)


def test_channel_authorization_and_management():
    manager = ChannelManager()

    # Pre-authorized channels
    assert manager.is_authorized(CommunicationChannel.EMAIL) is True
    assert manager.is_authorized(CommunicationChannel.CHAT) is True

    # Non-pre-authorized channel
    assert manager.is_authorized(CommunicationChannel.SMS) is False

    with pytest.raises(ChannelAuthorizationError):
        manager.verify_authorization(CommunicationChannel.SMS)

    # Authorize SMS explicitly
    manager.authorize_channel(CommunicationChannel.SMS, authorized=True)
    assert manager.is_authorized(CommunicationChannel.SMS) is True
    manager.verify_authorization(CommunicationChannel.SMS)


def test_channel_rate_limiting():
    manager = ChannelManager()
    manager.register_channel(CommunicationChannel.EMAIL, "Email", is_authorized=True, rate_limit_per_minute=3)

    now = datetime(2026, 9, 10, 10, 0, 0)
    # 3 allowed
    manager.check_rate_limit(CommunicationChannel.EMAIL, now=now)
    manager.check_rate_limit(CommunicationChannel.EMAIL, now=now)
    manager.check_rate_limit(CommunicationChannel.EMAIL, now=now)

    # 4th in same minute must raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError):
        manager.check_rate_limit(CommunicationChannel.EMAIL, now=now)


def test_channel_quiet_hours_and_critical_override():
    manager = ChannelManager()
    manager.register_channel(
        CommunicationChannel.EMAIL,
        "Email",
        is_authorized=True,
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
    )

    # During quiet hours (23:30)
    quiet_time = time(23, 30)
    with pytest.raises(QuietHoursViolationError):
        manager.check_quiet_hours(CommunicationChannel.EMAIL, current_time=quiet_time, urgency=CommunicationUrgency.NORMAL)

    # Critical override during quiet hours is permitted when allowed
    allowed = manager.check_quiet_hours(
        CommunicationChannel.EMAIL,
        current_time=quiet_time,
        urgency=CommunicationUrgency.CRITICAL,
        allow_critical_override=True,
    )
    assert allowed is True

    # Daytime (14:00) is permitted
    daytime = time(14, 0)
    assert manager.check_quiet_hours(CommunicationChannel.EMAIL, current_time=daytime) is True


def test_email_message_normalization():
    raw_email = {
        "from": "alice@example.com",
        "to": ["bob@example.com"],
        "cc": ["carol@example.com"],
        "subject": "Sprint Review",
        "body": "Let's review the sprint deliverables today.",
    }

    msg = MessageNormalizer.normalize_email(raw_email, user_id="user_123", project_id="proj_456")
    assert msg.channel == CommunicationChannel.EMAIL
    assert msg.sender == "alice@example.com"
    assert len(msg.recipients) == 2
    assert msg.subject == "Sprint Review"
    assert msg.content_reference == "Let's review the sprint deliverables today."
    assert msg.direction == MessageDirection.INBOUND
    assert msg.status == MessageStatus.DELIVERED
    assert msg.user_id == "user_123"
    assert msg.project_id == "proj_456"


def test_chat_message_normalization():
    raw_chat = {
        "user": "developer_dave",
        "text": "PR #42 is ready for review.",
        "channel_name": "engineering",
        "is_public": True,
    }

    msg = MessageNormalizer.normalize_chat(raw_chat, user_id="user_123")
    assert msg.channel == CommunicationChannel.CHAT
    assert msg.sender == "developer_dave"
    assert msg.content_reference == "PR #42 is ready for review."
    assert msg.privacy_scope == PrivacyScope.PUBLIC


def test_invariant_draft_cannot_be_sent():
    # INVARIANT 47: Draft != Sent
    with pytest.raises(ValueError, match="Draft message cannot be marked as SENT"):
        MessageNormalizer.normalize_generic(
            channel=CommunicationChannel.EMAIL,
            sender="alice@example.com",
            content="Hello world",
            direction=MessageDirection.DRAFT,
            status=MessageStatus.SENT,
        )
