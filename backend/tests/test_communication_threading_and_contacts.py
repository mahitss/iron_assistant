"""Unit tests for threading, cross-channel correlation, anti-false merging, and contact ambiguity."""

import pytest

from app.communication.contacts import (
    ContactAmbiguityError,
    ContactBook,
    ContactNotFoundError,
)
from app.communication.messages import MessageNormalizer
from app.communication.schemas import (
    CommunicationChannel,
    MessageDirection,
    MessageStatus,
    RecipientSchema,
    ThreadState,
)
from app.communication.threads import ThreadEngine, clean_subject


def test_clean_subject():
    assert clean_subject("Re: [Ticket-123] Server issue") == "[ticket-123] server issue"
    assert clean_subject("FWD: Project Roadmap") == "project roadmap"
    assert clean_subject("Hello") == "hello"


def test_thread_correlation_and_anti_false_merging():
    engine = ThreadEngine()

    msg1 = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="alice@example.com",
        content="First message regarding architecture.",
        subject="Architecture Proposal",
        recipients=[RecipientSchema(identity="bob@example.com", address="bob@example.com")],
    )
    thread1 = engine.correlate_message(msg1)

    # Reply with Re:
    msg2 = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="bob@example.com",
        content="Looks good, let's proceed.",
        subject="Re: Architecture Proposal",
        recipients=[RecipientSchema(identity="alice@example.com", address="alice@example.com")],
    )
    thread2 = engine.correlate_message(msg2)

    assert thread1.thread_id == thread2.thread_id
    assert len(thread1.messages) == 2

    # INVARIANT 21: Anti-false merging with generic subject ("Update")
    generic_msg1 = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="carol@example.com",
        content="Quick update on team schedule.",
        subject="Update",
    )
    generic_thread1 = engine.correlate_message(generic_msg1)

    generic_msg2 = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="dave@example.com",
        content="Update on database migration.",
        subject="Update",
    )
    generic_thread2 = engine.correlate_message(generic_msg2)

    # Generic subjects without references must NOT merge falsely
    assert generic_thread1.thread_id != generic_thread2.thread_id


def test_cross_channel_correlation_with_explicit_reference():
    engine = ThreadEngine()

    email_msg = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="support@vendor.com",
        content="Ticket #990 opened.",
        subject="Ticket #990 Incident",
    )
    thread = engine.correlate_message(email_msg)

    # Inbound Slack message with explicit cross-channel thread token
    chat_raw = {
        "user": "slack_bot",
        "text": "Status on Ticket #990 updated in Slack.",
        "headers": {"x-kairo-thread-ref": thread.thread_id},
    }
    chat_msg = MessageNormalizer.normalize_chat(chat_raw)
    chat_msg.provenance["cross_channel_ref"] = thread.thread_id

    correlated = engine.correlate_message(chat_msg)
    assert correlated.thread_id == thread.thread_id
    assert len(correlated.messages) == 2


def test_rolling_summary_generation():
    engine = ThreadEngine()
    msg = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="alice@example.com",
        content="We decided to launch on Friday.\nWhat time should we meet?",
        subject="Launch Planning",
    )
    thread = engine.correlate_message(msg)

    summary = engine.generate_rolling_summary(thread.thread_id)
    assert len(summary["open_questions"]) == 1
    assert "What time should we meet?" in summary["open_questions"][0]
    assert len(summary["decisions"]) >= 1


def test_contact_book_resolution_and_ambiguity_gating():
    book = ContactBook()
    book.add_contact(identity="john_doe", address="john.doe@company.com", display_name="John Doe")
    book.add_contact(identity="john_smith", address="john.smith@company.com", display_name="John Smith")

    # Unambiguous exact address match
    resolved = book.resolve_contact("john.doe@company.com")
    assert resolved.identity == "john_doe"

    # INVARIANT 11: Ambiguous contact match ("John") must raise ContactAmbiguityError!
    with pytest.raises(ContactAmbiguityError) as exc_info:
        book.resolve_contact("John")

    assert len(exc_info.value.candidates) == 2

    # Unknown query
    with pytest.raises(ContactNotFoundError):
        book.resolve_contact("unknown_alias")
