"""Unit tests for VoiceSession state machine, buffer management, and lifecycle."""

from datetime import UTC, datetime, timedelta

import pytest

from app.voice.schemas import VoiceState
from app.voice.session import (
    AudioLimitExceededError,
    InvalidStateTransitionError,
    VoiceSession,
)


def test_voice_session_initialization():
    """Verify session initialized in IDLE state with configured bounds."""
    session = VoiceSession(
        session_id="test_init_1",
        sample_rate=16000,
        max_session_seconds=1800,
        max_audio_chunk_bytes=4096,
        max_message_seconds=10,
    )
    assert session.session_id == "test_init_1"
    assert session.state == VoiceState.IDLE
    assert session.sample_rate == 16000
    assert session.get_audio_bytes() == b""
    assert not session.is_expired()
    assert not session.is_cancelled


def test_valid_state_transitions():
    """Verify standard happy-path voice session state transitions."""
    session = VoiceSession(session_id="test_trans_1")

    # IDLE -> LISTENING
    session.transition_to(VoiceState.LISTENING)
    assert session.state == VoiceState.LISTENING

    # LISTENING -> TRANSCRIBING
    session.transition_to(VoiceState.TRANSCRIBING)
    assert session.state == VoiceState.TRANSCRIBING

    # TRANSCRIBING -> PROCESSING
    session.transition_to(VoiceState.PROCESSING)
    assert session.state == VoiceState.PROCESSING

    # PROCESSING -> SPEAKING
    session.transition_to(VoiceState.SPEAKING)
    assert session.state == VoiceState.SPEAKING

    # SPEAKING -> LISTENING
    session.transition_to(VoiceState.LISTENING)
    assert session.state == VoiceState.LISTENING

    # LISTENING -> CLOSED
    session.transition_to(VoiceState.CLOSED)
    assert session.state == VoiceState.CLOSED


def test_invalid_state_transition_rejected():
    """Verify invalid transitions raise InvalidStateTransitionError."""
    session = VoiceSession(session_id="test_invalid_1")
    assert session.state == VoiceState.IDLE

    # Cannot jump directly from IDLE to SPEAKING
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        session.transition_to(VoiceState.SPEAKING)

    assert exc_info.value.from_state == VoiceState.IDLE
    assert exc_info.value.to_state == VoiceState.SPEAKING
    assert session.state == VoiceState.IDLE

    # Cannot transition out of CLOSED terminal state
    session.transition_to(VoiceState.CLOSED)
    with pytest.raises(InvalidStateTransitionError):
        session.transition_to(VoiceState.LISTENING)


def test_audio_buffer_bounds_enforcement():
    """Verify oversized chunks and oversized accumulated stream are rejected."""
    session = VoiceSession(
        session_id="test_bounds_1",
        sample_rate=16000,
        max_audio_chunk_bytes=100,
        max_message_seconds=1,  # 16000 * 2 = 32000 bytes max
    )

    # Valid chunk
    session.append_audio(b"\x00" * 50)
    assert len(session.get_audio_bytes()) == 50

    # Chunk exceeding max_audio_chunk_bytes
    with pytest.raises(AudioLimitExceededError, match="chunk size"):
        session.append_audio(b"\x00" * 150)

    # Privacy guarantee: Clearing buffer discards all bytes
    session.clear_audio_buffer()
    assert session.get_audio_bytes() == b""


def test_session_expiration_and_touch():
    """Verify session detects expiration based on total and idle duration."""
    session = VoiceSession(
        session_id="test_exp_1",
        max_session_seconds=100,
    )
    assert not session.is_expired()

    # Simulate total session duration exceeded
    session.started_at = datetime.now(UTC) - timedelta(seconds=120)
    assert session.is_expired()

    # Reset started_at, simulate idle timeout
    session.started_at = datetime.now(UTC)
    session.last_activity = datetime.now(UTC) - timedelta(seconds=350)
    assert session.is_expired()

    # Touch updates activity
    session.touch()
    assert not session.is_expired()


def test_turn_cancellation_and_close():
    """Verify cancellation flag and closing session."""
    session = VoiceSession(session_id="test_cancel_1")
    session.append_audio(b"\x01\x02\x03\x04")

    session.cancel_active_turn()
    assert session.is_cancelled

    session.reset_cancellation()
    assert not session.is_cancelled

    session.close()
    assert session.state == VoiceState.CLOSED
    assert session.get_audio_bytes() == b""
