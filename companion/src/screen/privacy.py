"""Screen privacy validator and active capture indicator manager."""

import logging
import time

logger = logging.getLogger("kairo.companion.screen.privacy")


class ScreenPrivacyManager:
    """Manages explicit screen capture notices and rate limiting."""

    def __init__(self, min_interval_seconds: float = 1.0) -> None:
        self.min_interval = min_interval_seconds
        self._last_capture_time = 0.0
        self._capture_in_progress = False

    def is_sharing_active(self) -> bool:
        """Return whether screen sharing or observation is actively in progress."""
        return self._capture_in_progress

    def notify_capture_start(self, destination: str) -> None:
        """Record capture initiation and check rate limit."""
        now = time.time()
        if (now - self._last_capture_time) < self.min_interval:
            raise PermissionError(
                f"Screen capture throttled: minimum interval of {self.min_interval}s enforced."
            )

        self._capture_in_progress = True
        self._last_capture_time = now
        logger.info("[PRIVACY BADGE] Screen capture active -> destination: %s", destination)

    def notify_capture_end(self) -> None:
        """Clear active indicator."""
        self._capture_in_progress = False
        logger.info("[PRIVACY BADGE] Screen capture ended.")
