"""Companion runtime lifecycle state manager enforcing safe default OFF semantics."""

import logging
import time
from enum import Enum

logger = logging.getLogger("kairo.companion.state")


class CompanionState(str, Enum):
    """Authoritative lifecycle and computer control states."""

    OFF = "OFF"
    READY = "READY"
    ARMED = "ARMED"
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    REVOKED = "REVOKED"


class DeviceStateManager:
    """Manages runtime computer control states, auto-timeout decay, and safe startup resets."""

    def __init__(self, inactivity_timeout_seconds: float = 900.0) -> None:
        self._state: CompanionState = CompanionState.OFF  # Default OFF!
        self._inactivity_timeout = inactivity_timeout_seconds
        self._last_activity_time = time.time()
        self._capabilities = {
            "computer_control": False,
            "microphone": False,
            "camera": False,
            "filesystem": False,
        }

    @property
    def current_state(self) -> CompanionState:
        """Return active companion state with automatic inactivity decay to OFF."""
        if self._state in (CompanionState.ARMED, CompanionState.ACTIVE):
            if (time.time() - self._last_activity_time) > self._inactivity_timeout:
                logger.warning("Prolonged inactivity detected. Reverting state to OFF.")
                self.reset_to_safe_off()
        return self._state

    def reset_to_safe_off(self) -> None:
        """Immediately reset all capabilities and states to OFF (safe default)."""
        self._state = CompanionState.OFF
        for k in self._capabilities:
            self._capabilities[k] = False
        self._last_activity_time = time.time()
        logger.info("Companion reset to safe OFF state. All capabilities disabled.")

    def transition_to(self, new_state: CompanionState, reason: str = "") -> None:
        """Explicit state transition with safety enforcement."""
        if self._state == CompanionState.REVOKED and new_state != CompanionState.REVOKED:
            raise PermissionError("Cannot transition out of REVOKED state. Device must be re-registered.")

        if self._state == CompanionState.STOPPED and new_state not in (
            CompanionState.OFF,
            CompanionState.STOPPED,
        ):
            raise PermissionError("Emergency Stop is ACTIVE. Must explicitly reset to OFF before arming.")

        logger.info("State transition: %s -> %s (reason: %s)", self._state.value, new_state.value, reason)
        self._state = new_state
        self._last_activity_time = time.time()

    def set_capability(self, capability: str, enabled: bool) -> None:
        """Toggle a specific hardware capability."""
        if capability not in self._capabilities:
            raise KeyError(f"Unknown capability: {capability}")
        if (
            self.current_state in (CompanionState.OFF, CompanionState.STOPPED, CompanionState.REVOKED)
            and enabled
        ):
            raise PermissionError(
                f"Cannot enable capability '{capability}' while state is {self._state.value}."
            )

        self._capabilities[capability] = enabled
        self._last_activity_time = time.time()

    def is_capability_enabled(self, capability: str) -> bool:
        """Check whether a capability is actively permitted."""
        if self.current_state in (CompanionState.OFF, CompanionState.STOPPED, CompanionState.REVOKED):
            return False
        return self._capabilities.get(capability, False)

    def record_activity(self) -> None:
        """Refresh inactivity heartbeat."""
        self._last_activity_time = time.time()

    def get_status_summary(self) -> dict:
        """Return safe telemetry summary."""
        return {
            "state": self.current_state.value,
            "capabilities": dict(self._capabilities),
            "idle_seconds": round(time.time() - self._last_activity_time, 1),
        }
