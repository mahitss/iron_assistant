"""Companion transport client managing connection lifecycle, safe reconnection, and offline containment."""

import logging
from enum import Enum
from typing import Any

from companion.src.auth.credentials import LocalCredentialVault
from companion.src.device.state import CompanionState, DeviceStateManager

logger = logging.getLogger("kairo.companion.transport.client")


class SessionState(str, Enum):
    """Session connection lifecycle states."""

    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    REVOKED = "REVOKED"


class CompanionTransportClient:
    """Manages connection to Kairo Cloud, token renewal, session lifecycle, and offline fallback."""

    def __init__(
        self,
        vault: LocalCredentialVault | None = None,
        state_manager: DeviceStateManager | None = None,
    ) -> None:
        self.vault = vault or LocalCredentialVault()
        self.state_manager = state_manager or DeviceStateManager()
        self._session_state = SessionState.DISCONNECTED
        self._consecutive_auth_failures = 0
        self._pending_commands_queue: list[dict[str, Any]] = []

    @property
    def session_state(self) -> SessionState:
        return self._session_state

    def connect(self) -> bool:
        """Establish authenticated session with Kairo Cloud."""
        if self._session_state == SessionState.REVOKED:
            logger.error("Device is REVOKED. Cannot connect.")
            return False

        if self._consecutive_auth_failures >= 3:
            logger.error("Max consecutive authentication failures reached. Halting reconnection.")
            self._session_state = SessionState.DISCONNECTED
            return False

        self._session_state = SessionState.CONNECTING
        logger.info("Connecting to Kairo Cloud...")

        creds = self.vault.load_credentials()
        if not creds or not creds.get("device_token"):
            logger.warning("No credentials found in vault. Device must be registered.")
            self._session_state = SessionState.DISCONNECTED
            return False

        # Authenticate device token
        self._session_state = SessionState.AUTHENTICATING
        try:
            # Simulate authentication handshake with cloud endpoint
            status = creds.get("status", "ACTIVE")
            if status == "REVOKED":
                self._session_state = SessionState.REVOKED
                self.vault.clear_credentials()
                self.state_manager.transition_to(CompanionState.REVOKED, "Server revoked device")
                return False

            self._session_state = SessionState.CONNECTED
            self._consecutive_auth_failures = 0
            logger.info("Companion session CONNECTED. Device ID: %s", creds.get("device_id"))
            return True

        except Exception as exc:
            self._consecutive_auth_failures += 1
            self._session_state = SessionState.DISCONNECTED
            logger.error("Authentication failed: %s (attempts: %d)", exc, self._consecutive_auth_failures)
            return False

    def handle_disconnect(self, reason: str = "Network loss") -> None:
        """Handle disconnection: clear pending commands and revert risky states."""
        logger.warning("Transport disconnected: %s. Entering offline mode.", reason)
        self._session_state = SessionState.DISCONNECTED

        # Offline containment: clear all queued pending risky commands
        purged_count = len(self._pending_commands_queue)
        self._pending_commands_queue.clear()
        logger.info("Cleared %d pending commands due to disconnection.", purged_count)

        # Restore safe OFF state
        self.state_manager.reset_to_safe_off()

    def handle_revocation(self) -> None:
        """Handle server-side device revocation immediately."""
        logger.critical("Device revocation signal received. Terminating companion session.")
        self._session_state = SessionState.REVOKED
        self._pending_commands_queue.clear()
        self.vault.clear_credentials()
        self.state_manager.reset_to_safe_off()
        self.state_manager.transition_to(CompanionState.REVOKED, "Device revoked by user")

    def enqueue_command(self, command: dict[str, Any]) -> None:
        """Queue command only if connected."""
        if self._session_state != SessionState.CONNECTED:
            raise ConnectionError("Cannot queue commands in disconnected or offline mode.")
        self._pending_commands_queue.append(command)

    def get_next_command(self) -> dict[str, Any] | None:
        """Pop next command from queue."""
        if not self._pending_commands_queue:
            return None
        return self._pending_commands_queue.pop(0)
