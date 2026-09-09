"""Local Emergency Stop manager providing instant, fail-safe hardware cutoff."""

import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger("kairo.companion.security.emergency_stop")


class LocalEmergencyStop:
    """Atomic local Emergency Stop controller operating independently of cloud network connectivity."""

    def __init__(self) -> None:
        self._stopped = threading.Event()
        self._halt_callbacks: list[Callable[[], None]] = []
        self._stop_timestamp: float | None = None
        self._reason: str | None = None

    @property
    def is_stopped(self) -> bool:
        """Check whether local Emergency Stop is currently engaged."""
        return self._stopped.is_set()

    def register_halt_callback(self, callback: Callable[[], None]) -> None:
        """Register hardware cutoff routine (e.g. drop mouse, release keyboard, close mic/cam)."""
        self._halt_callbacks.append(callback)

    def trigger_stop(self, reason: str = "Local Emergency Stop Triggered") -> None:
        """Engage immediate emergency halt across all companion capabilities."""
        self._stopped.set()
        self._stop_timestamp = time.time()
        self._reason = reason

        logger.critical("!!! LOCAL EMERGENCY STOP ENGAGED !!! Reason: %s", reason)

        # Fire all hardware cutoff routines immediately
        for cb in self._halt_callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("Error executing emergency cutoff callback: %s", exc)

    def reset_stop(self) -> None:
        """Reset emergency stop back to safe unhalted state (requires explicit operator action)."""
        self._stopped.clear()
        self._stop_timestamp = None
        self._reason = None
        logger.warning("Local Emergency Stop reset. Capabilities remain OFF until explicitly armed.")

    def get_status(self) -> dict:
        return {
            "emergency_stop_active": self.is_stopped,
            "stop_timestamp": self._stop_timestamp,
            "reason": self._reason,
        }
