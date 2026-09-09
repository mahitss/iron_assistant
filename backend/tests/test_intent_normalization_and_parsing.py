"""Unit tests for Command Normalization, speech artifact cleaning, and raw input preservation (Spec 6, 7, 8, 9, 10)."""

import pytest

from app.intent.normalizer import CommandNormalizer
from app.intent.parser import IntentParser
from app.intent.schemas import CommandAttachment, IntentType


def test_command_normalizer_preserves_original_text():
    """Verify original text is strictly preserved unaltered (Spec 7)."""
    raw = "   hey kairo, uh, can you please   check the build???   "
    original, normalized = CommandNormalizer.normalize(raw)

    assert original == raw
    assert normalized == "can you please check the build?"
    assert "hey kairo" not in normalized.lower()
    assert "uh" not in normalized


def test_command_normalizer_speech_fillers_and_stutters():
    """Verify benign speech-to-text artifacts like stutters and fillers are cleaned (Spec 6)."""
    raw = "um, like, what is the the current status of the the deployment?"
    original, normalized = CommandNormalizer.normalize(raw)

    assert original == raw
    assert "the the" not in normalized
    assert "um" not in normalized
    assert normalized == "what is the current status of the deployment?"


def test_command_parser_multimodal_attachment_target():
    """Verify attached media is correctly linked as target for ANALYZE intent (Spec 9, 10)."""
    attachment = CommandAttachment(
        type="image",
        name="error_screenshot.png",
        url="http://local/media/error.png",
    )

    cmd_schema, intent_schema = IntentParser.parse_command(
        raw_text="What's wrong with this?",
        user_id="user_test_1",
        attachments=[attachment],
    )

    assert intent_schema.type == IntentType.ANALYZE
    assert intent_schema.target is not None
    assert intent_schema.target.entity_type == "attachment"
    assert intent_schema.target.name == "error_screenshot.png"
    assert cmd_schema.original_text == "What's wrong with this?"
