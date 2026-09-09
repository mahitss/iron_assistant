"""Unit tests for 14 message classification categories, communication intent, and action extraction."""

from app.communication.classifier import MessageClassifier
from app.communication.intent import CommunicationIntentEngine
from app.communication.messages import MessageNormalizer
from app.communication.schemas import CommunicationChannel, MessageCategory


def test_14_message_classification_categories():
    classifier = MessageClassifier()

    # Question
    msg_q = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="alice@example.com",
        content="Could you please explain what time the release is scheduled for?",
    )
    assert classifier.classify(msg_q)["primary_category"] == MessageCategory.QUESTION.value

    # Alert
    msg_alert = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="ops@example.com",
        content="ALERT: Critical incident in production cluster!",
    )
    assert classifier.classify(msg_alert)["primary_category"] == MessageCategory.ALERT.value

    # Approval
    msg_appr = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="lead@example.com",
        content="LGTM! Approved for deployment.",
    )
    assert classifier.classify(msg_appr)["primary_category"] == MessageCategory.APPROVAL.value

    # Thanks
    msg_thanks = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="client@example.com",
        content="Thank you so much for the quick turnaround, appreciate your help!",
    )
    assert classifier.classify(msg_thanks)["primary_category"] == MessageCategory.THANKS.value


def test_intent_engine_action_and_deadline_extraction():
    intent_engine = CommunicationIntentEngine()

    msg = MessageNormalizer.normalize_generic(
        channel=CommunicationChannel.EMAIL,
        sender="manager@example.com",
        content="Please send the financial summary by Friday at 5pm.\nBob will review the security checklist before tomorrow morning.",
        subject="Action Items",
    )

    result = intent_engine.extract_intent_and_actions(msg)
    assert result["communication_goal"] == "request"
    actions = result["actions"]
    assert len(actions) >= 2

    # Check extracted deadline text (without inventing dates!)
    first_action = actions[0]
    assert "financial summary" in first_action["action"]
    assert first_action["deadline_text"] is not None
    assert "friday" in first_action["deadline_text"].lower()

    # Second action attributed to Bob
    second_action = actions[1]
    assert second_action["owner"].lower() == "bob"
