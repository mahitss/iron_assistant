"""Audio speaker and TTS playback controller with instant cancel/stop controls."""

import logging
from typing import Any

from companion.src.actions.base import BaseCompanionAction

logger = logging.getLogger("kairo.companion.audio.speaker")


class SpeakerManager:
    """Manages audio playback, volume muting, and instant cancellation."""

    def __init__(self) -> None:
        self._is_playing = False
        self._is_muted = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_muted(self, muted: bool) -> None:
        self._is_muted = muted
        logger.info("[SPEAKER] Mute state set to: %s", muted)

    def cancel_playback(self) -> None:
        """Immediately interrupt and stop any active audio playback."""
        if self._is_playing:
            self._is_playing = False
            logger.info("[SPEAKER] Audio playback cancelled by user/system command.")

    def play_tts(self, text: str, voice: str = "default") -> bool:
        """Simulate playing TTS audio."""
        if self._is_muted:
            logger.info("[SPEAKER] Speaker muted, skipping playback.")
            return False

        self._is_playing = True
        logger.info("[SPEAKER] Playing TTS text (%d chars) [voice=%s]", len(text), voice)
        self._is_playing = False
        return True


class AudioPlayAction(BaseCompanionAction):
    """Action for playing TTS or audio notifications through the local companion."""

    def __init__(self, speaker_manager: SpeakerManager | None = None) -> None:
        super().__init__(name="audio.play", default_timeout_seconds=15.0)
        self.speaker_manager = speaker_manager or SpeakerManager()

    def run(self, parameters: dict[str, Any]) -> dict[str, Any]:
        text = str(parameters.get("text", "")).strip()
        if not text:
            raise ValueError("Parameter 'text' is required for audio.play.")

        voice = parameters.get("voice", "default")
        played = self.speaker_manager.play_tts(text, voice)
        return {"played": played, "characters": len(text), "voice": voice}
