"""VoiceSession state machine managing session lifecycle, audio buffer, and limits."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from app.voice.schemas import VoiceState

logger = logging.getLogger("kairo.voice.session")


class InvalidStateTransitionError(ValueError):
    """Raised when attempting an unauthorized VoiceState transition."""

    def __init__(self, from_state: VoiceState, to_state: VoiceState):
        super().__init__(f"Invalid voice state transition: '{from_state.value}' -> '{to_state.value}'")
        self.from_state = from_state
        self.to_state = to_state


class AudioLimitExceededError(ValueError):
    """Raised when audio chunk or stream exceeds configured bounds."""


# Allowed directed transitions between VoiceStates
VALID_TRANSITIONS: dict[VoiceState, set[VoiceState]] = {
    VoiceState.IDLE: {
        VoiceState.LISTENING,
        VoiceState.CLOSED,
        VoiceState.ERROR,
    },
    VoiceState.LISTENING: {
        VoiceState.TRANSCRIBING,
        VoiceState.STOPPING,
        VoiceState.CLOSED,
        VoiceState.ERROR,
    },
    VoiceState.TRANSCRIBING: {
        VoiceState.PROCESSING,
        VoiceState.LISTENING,  # If speech was silence or empty
        VoiceState.STOPPING,
        VoiceState.CLOSED,
        VoiceState.ERROR,
    },
    VoiceState.PROCESSING: {
        VoiceState.SPEAKING,
        VoiceState.LISTENING,  # Interrupted or text-only fallback
        VoiceState.STOPPING,
        VoiceState.CLOSED,
        VoiceState.ERROR,
    },
    VoiceState.SPEAKING: {
        VoiceState.LISTENING,  # Speech playback completed or user interrupted
        VoiceState.STOPPING,
        VoiceState.CLOSED,
        VoiceState.ERROR,
    },
    VoiceState.STOPPING: {
        VoiceState.LISTENING,
        VoiceState.CLOSED,
        VoiceState.ERROR,
    },
    VoiceState.CLOSED: set(),  # Terminal state
    VoiceState.ERROR: {
        VoiceState.LISTENING,  # Recovery
        VoiceState.CLOSED,
    },
}


class VoiceSession:
    """Manages real-time voice state, ephemeral audio buffer, and processing lifecycle."""

    def __init__(
        self,
        session_id: str,
        sample_rate: int = 16000,
        max_session_seconds: int = 1800,
        max_audio_chunk_bytes: int = 65536,
        max_message_seconds: int = 60,
    ) -> None:
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.max_session_seconds = max_session_seconds
        self.max_audio_chunk_bytes = max_audio_chunk_bytes
        # 16-bit mono PCM = 2 bytes per sample
        bytes_per_second = sample_rate * 2
        self.max_message_bytes = max_message_seconds * bytes_per_second

        self.started_at = datetime.now(UTC)
        self.last_activity = datetime.now(UTC)
        self.state: VoiceState = VoiceState.IDLE

        # Ephemeral audio buffer for current speech turn (cleared immediately after STT)
        self._audio_buffer: bytearray = bytearray()
        self.active_task: asyncio.Task[Any] | None = None
        self._cancellation_requested: bool = False
        self.last_transcript: str | None = None

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(UTC)

    def transition_to(self, new_state: VoiceState) -> None:
        """Transition session to a new state if valid under transition policy."""
        self.touch()
        if new_state == self.state:
            return

        allowed = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            logger.warning(
                "Rejected invalid state transition for session '%s': %s -> %s",
                self.session_id,
                self.state.value,
                new_state.value,
            )
            raise InvalidStateTransitionError(self.state, new_state)

        logger.debug(
            "Session '%s' state transition: %s -> %s",
            self.session_id,
            self.state.value,
            new_state.value,
        )
        self.state = new_state

    def append_audio(self, chunk: bytes) -> None:
        """Append raw PCM/WAV audio bytes with bounds enforcement."""
        self.touch()
        if not chunk:
            return

        chunk_len = len(chunk)
        if chunk_len > self.max_audio_chunk_bytes:
            raise AudioLimitExceededError(
                f"Audio chunk size {chunk_len} bytes exceeds maximum permitted {self.max_audio_chunk_bytes} bytes."
            )

        if len(self._audio_buffer) + chunk_len > self.max_message_bytes:
            raise AudioLimitExceededError(
                f"Total audio buffer exceeded message duration limit ({self.max_message_bytes} bytes)."
            )

        self._audio_buffer.extend(chunk)

    def get_audio_bytes(self) -> bytes:
        """Retrieve accumulated audio bytes."""
        return bytes(self._audio_buffer)

    def clear_audio_buffer(self) -> None:
        """Immediately discard raw audio buffer (privacy safeguard)."""
        self._audio_buffer.clear()

    def is_expired(self) -> bool:
        """Check whether total session or idle duration has exceeded bounds."""
        now = datetime.now(UTC)
        total_duration = (now - self.started_at).total_seconds()
        idle_duration = (now - self.last_activity).total_seconds()

        # Session expires if total duration exceeds limit or idle > 300s
        return total_duration > self.max_session_seconds or idle_duration > 300

    def cancel_active_turn(self) -> None:
        """Cancel ongoing Kairo processing or TTS synthesis (interruption / barge-in)."""
        self._cancellation_requested = True
        if self.active_task and not self.active_task.done():
            logger.info("Cancelling active processing task for session '%s'", self.session_id)
            self.active_task.cancel()
            self.active_task = None

    def reset_cancellation(self) -> None:
        """Reset cancellation flag for next turn."""
        self._cancellation_requested = False

    @property
    def is_cancelled(self) -> bool:
        """Check if current turn was cancelled by user interruption."""
        return self._cancellation_requested

    def close(self) -> None:
        """Close session and cancel any running tasks."""
        self.cancel_active_turn()
        self.clear_audio_buffer()
        self.state = VoiceState.CLOSED
