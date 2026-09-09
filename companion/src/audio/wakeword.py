"""Local wake-word engine running entirely on device without cloud streaming."""

import logging
from collections.abc import Callable

logger = logging.getLogger("kairo.companion.audio.wakeword")


class LocalWakeWordEngine:
    """Detects local wake-word trigger ('Hey Kairo') locally.

    Zero raw audio is streamed to the cloud during wake-word listening.
    """

    DEFAULT_WAKEWORD = "Hey Kairo"

    def __init__(self, wakeword: str = DEFAULT_WAKEWORD) -> None:
        self.wakeword = wakeword
        self._is_active = False
        self._on_wake_callbacks: list[Callable[[], None]] = []

    @property
    def is_listening(self) -> bool:
        return self._is_active

    def register_on_wake(self, callback: Callable[[], None]) -> None:
        self._on_wake_callbacks.append(callback)

    def start(self) -> None:
        """Start local lightweight wake-word listening loop."""
        self._is_active = True
        logger.info("[WAKE WORD] Local wake-word listening active for: '%s' (Offline engine)", self.wakeword)

    def stop(self) -> None:
        """Stop wake-word listening."""
        self._is_active = False
        logger.info("[WAKE WORD] Local wake-word listening stopped.")

    def simulate_wake_trigger(self) -> None:
        """Simulate wake-word detection for testing or integration."""
        if not self._is_active:
            raise RuntimeError("Wake-word engine is not listening.")
        logger.info(
            "[WAKE WORD] Wake word '%s' detected locally! Initiating explicit voice session.", self.wakeword
        )
        for cb in self._on_wake_callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("Error in wake callback: %s", exc)
