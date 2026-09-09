"""Unit tests for delivery state, tool dispatch, idempotency, retries, and scheduling revocation."""

from datetime import UTC, datetime, timedelta
import pytest

from app.communication.delivery import (
    BlindResendError,
    BulkCommunicationAuthorizationError,
    DeliveryManager,
    DuplicateSendError,
)
from app.communication.scheduling import (
    RevalidationFailedError,
    ScheduleRevokedError,
    ScheduledMessageEngine,
)
from app.communication.schemas import (
    CommunicationChannel,
    DraftMessageSchema,
    DraftStatus,
    MessageStatus,
    RecipientSchema,
    SendRequestSchema,
)


def test_delivery_dispatch_and_idempotency():
    manager = DeliveryManager()
    recipients = [RecipientSchema(identity="alice@example.com", address="alice@example.com")]

    req = SendRequestSchema(
        channel=CommunicationChannel.EMAIL,
        recipients=recipients,
        subject="Sync Meeting",
        content="Let's sync up tomorrow.",
        idempotency_key="idemp_key_12345",
    )

    receipt = manager.dispatch(req)
    assert receipt.status in (MessageStatus.SENT, MessageStatus.DELIVERED)
    # INVARIANT 113: Delivery != Read
    assert receipt.read_receipt is False

    # INVARIANT 117: Duplicate send with identical idempotency key must raise DuplicateSendError
    with pytest.raises(DuplicateSendError):
        manager.dispatch(req)


def test_safe_retry_blocks_blind_resend_on_unknown():
    manager = DeliveryManager()
    receipt_id = "rec_unknown_1"
    # Manually populate unknown receipt
    manager._receipts[receipt_id] = manager.dispatch(
        SendRequestSchema(
            channel=CommunicationChannel.EMAIL,
            recipients=[RecipientSchema(identity="a@b.com", address="a@b.com")],
            content="test",
        )
    )
    manager._receipts[receipt_id].status = MessageStatus.UNKNOWN

    # INVARIANT 116 & 119: Blind resend without state check must fail
    with pytest.raises(BlindResendError):
        manager.safe_retry(receipt_id, verified_not_received=False)

    # Safe retry with state check succeeds
    retried = manager.safe_retry(receipt_id, verified_not_received=True)
    assert retried.status == MessageStatus.DELIVERED


def test_bulk_communication_protection():
    manager = DeliveryManager()
    # 12 recipients (> 10)
    bulk_recipients = [
        RecipientSchema(identity=f"user_{i}@example.com", address=f"user_{i}@example.com")
        for i in range(12)
    ]

    req = SendRequestSchema(
        channel=CommunicationChannel.EMAIL,
        recipients=bulk_recipients,
        content="Broadcast announcement",
    )

    # INVARIANT 122: Bulk send requires explicit authorization
    with pytest.raises(BulkCommunicationAuthorizationError):
        manager.dispatch(req, allow_bulk=False)

    # Allowed with explicit authorization
    receipt = manager.dispatch(req, allow_bulk=True)
    assert receipt.status in (MessageStatus.SENT, MessageStatus.DELIVERED)


def test_scheduling_and_instant_revocation():
    sched_engine = ScheduledMessageEngine()
    future_time = datetime.now(UTC) + timedelta(days=1)
    recipients = [RecipientSchema(identity="alice@example.com", address="alice@example.com")]

    record = sched_engine.schedule_send(
        draft_id="draft_1",
        channel=CommunicationChannel.EMAIL,
        recipients=recipients,
        scheduled_time=future_time,
        user_id="user_test",
    )
    assert record["status"] == "SCHEDULED"

    # Pre-send revalidation succeeds
    draft = DraftMessageSchema(draft_id="draft_1", body_reference="test", status=DraftStatus.APPROVED)
    sched_engine.revalidate_before_send(record["schedule_id"], current_draft=draft)

    # User revokes communication permissions
    sched_engine.revoke_user_permissions("user_test")

    # INVARIANT 132 & 195: Revoked user cannot execute scheduled send
    with pytest.raises(ScheduleRevokedError):
        sched_engine.revalidate_before_send(record["schedule_id"], current_draft=draft)
