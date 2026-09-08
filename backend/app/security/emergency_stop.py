"""Emergency Stop service providing immediate kill-switch protection against active side-effects."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.security.exceptions import EmergencyStopActiveError, SecurityError
from app.security.permissions import PermissionLevel

logger = logging.getLogger("kairo.security.emergency_stop")


class EmergencyStopService:
    """Manages active vs stopped emergency state.

    CRITICAL RULES:
    1. The model cannot disable or reset the emergency stop.
    2. When STOPPED, all WRITE, EXECUTE, EXTERNAL, and DESTRUCTIVE actions are blocked immediately.
    3. Safe READ actions may remain accessible.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        # In-memory fallback map: user_id -> { "stopped": bool, "timestamp": str, "reason": str }
        self._local_state: dict[str, dict[str, Any]] = {}
        self._global_stopped: bool = False

    def trigger_emergency_stop(
        self, user_id: str | None = None, reason: str = "User initiated stop"
    ) -> dict[str, Any]:
        """Activate the emergency kill switch globally or for a specific user."""
        now_str = datetime.now(UTC).isoformat()
        info = {
            "stopped": True,
            "timestamp": now_str,
            "reason": reason,
        }

        if user_id:
            self._local_state[user_id] = info
            logger.critical("EMERGENCY STOP ACTIVATED for user '%s': %s", user_id, reason)
        else:
            self._global_stopped = True
            logger.critical("GLOBAL EMERGENCY STOP ACTIVATED: %s", reason)

        return info

    def reset_emergency_stop(self, user_id: str | None = None, is_human_user: bool = True) -> bool:
        """Reset the emergency stop. Strictly requires explicit user confirmation."""
        if not is_human_user:
            raise SecurityError("Unauthorized: The AI model cannot reset an emergency stop.")

        if user_id and user_id in self._local_state:
            self._local_state[user_id]["stopped"] = False
            logger.info("Emergency stop reset for user '%s'.", user_id)
        else:
            self._global_stopped = False
            logger.info("Global emergency stop reset.")

        return True

    def is_stopped(self, user_id: str | None = None) -> bool:
        """Check whether emergency stop is currently active."""
        if self._global_stopped:
            return True
        if user_id and user_id in self._local_state:
            return bool(self._local_state[user_id].get("stopped", False))
        return False

    def verify_can_execute(
        self, tool_name: str, permission_level: PermissionLevel, user_id: str | None = None
    ) -> None:
        """Raise EmergencyStopActiveError if stopped and tool has side-effects."""
        if not self.is_stopped(user_id):
            return

        # Safe read operations may proceed; all side-effecting operations are halted
        if permission_level == PermissionLevel.READ:
            return

        raise EmergencyStopActiveError(
            f"Emergency stop is ACTIVE. Side-effecting action '{tool_name}' ({permission_level.value}) is blocked."
        )


# Global singleton instance for application lifetime
_global_emergency_stop: EmergencyStopService | None = None


def get_emergency_stop_service() -> EmergencyStopService:
    """Retrieve or create the process-wide EmergencyStopService singleton."""
    global _global_emergency_stop
    if _global_emergency_stop is None:
        _global_emergency_stop = EmergencyStopService()
    return _global_emergency_stop
