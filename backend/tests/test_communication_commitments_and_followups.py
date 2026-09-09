"""Unit tests for commitment tracking, anti-fabrication guards, and bounded follow-ups."""

from datetime import UTC, datetime, timedelta
import pytest

from app.communication.commitments import (
    CommitmentFabricationError,
    CommitmentTracker,
)
from app.communication.followups import (
    FollowUpEngine,
    FollowUpLimitExceededError,
)
from app.communication.messages import MessageNormalizer
from app.communication.schemas import (
    CommitmentStatus,
    CommunicationChannel,
    FollowUpTrigger,
    MessageDirection,
)


def test_commitment_extraction_and_anti_fabrication():
    tracker = CommitmentTracker()

    # User commitment in outbound message ("I will...")
    msg_out = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="user@kairo.internal",
        content="I will deliver the API documentation by 4pm today.",
        direction=MessageDirection.OUTBOUND,
    )
    extracted = tracker.extract_commitments_from_message(msg_out, current_user_identity="user@kairo.internal")
    assert len(extracted) == 1
    assert "deliver the API documentation" in extracted[0].statement
    assert extracted[0].owner == "user@kairo.internal"
    assert extracted[0].status == CommitmentStatus.OPEN

    # Third-party commitment in inbound message ("Dave will...")
    msg_in = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="lead@example.com",
        content="Dave will configure the staging database before the demo.",
        direction=MessageDirection.INBOUND,
    )
    extracted_third = tracker.extract_commitments_from_message(msg_in)
    assert len(extracted_third) == 1
    assert extracted_third[0].owner == "Dave"

    # Anti-fabrication check: empty statements cannot be made into commitments
    with pytest.raises(CommitmentFabricationError):
        tracker.create_explicit_commitment(statement="", owner="user@kairo.internal")

    with pytest.raises(CommitmentFabricationError):
        tracker.create_explicit_commitment(statement="Valid statement", owner="")


def test_followup_bounds_and_anti_spam():
    engine = FollowUpEngine(max_default_attempts=2)

    fu = engine.schedule_followup(
        thread_id="thread_123",
        owner="user@kairo.internal",
        action="Check if deployment approval arrived",
        trigger=FollowUpTrigger.NO_RESPONSE,
        max_attempts=2,
    )
    assert fu.attempts_count == 0
    assert fu.max_attempts == 2

    # First attempt
    engine.record_attempt(fu.followup_id)
    assert fu.attempts_count == 1
    assert fu.status == "OPEN"

    # Second attempt (reaches limit)
    engine.record_attempt(fu.followup_id)
    assert fu.attempts_count == 2
    assert fu.status == "EXHAUSTED"

    # INVARIANT 34 & 134: Third attempt must raise FollowUpLimitExceededError to prevent infinite spam loops
    with pytest.raises(FollowUpLimitExceededError):
        engine.record_attempt(fu.followup_id)


def test_response_interpretation_silence_not_rejection():
    engine = FollowUpEngine()

    # Affirmative response
    msg_yes = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="partner@example.com",
        content="Yes, sounds good. Approved!",
    )
    assert engine.interpret_response(msg_yes) == "positive_response"

    # Negative response
    msg_no = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="partner@example.com",
        content="We decline the offer and must cancel.",
    )
    assert engine.interpret_response(msg_no) == "negative_response"

    # Ambiguous response
    msg_ambig = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="partner@example.com",
        content="Maybe next quarter, not sure yet.",
    )
    assert engine.interpret_response(msg_ambig) == "ambiguous_response"
