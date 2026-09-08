"""Cooldown and condition transition tracking to avoid repeated alerts on unchanged states."""

import logging
from typing import Any

logger = logging.getLogger("kairo.proactive.cooldown")

# In-memory transition state cache fallback (key -> last_state_value)
_LOCAL_STATE_CACHE: dict[str, str] = {}


class CooldownTracker:
    """Tracks condition transitions (e.g. SUCCESS -> FAILURE, UP -> DOWN).

    Suppresses alerts if the monitored resource remains in the same failing state,
    but re-alerts immediately when a transition occurs.
    """

    @classmethod
    def make_state_key(
        cls, user_id: str, source_type: str, source_id: str | None, state_key: str | None
    ) -> str:
        """Construct normalized state key."""
        return f"{user_id}:{source_type}:{source_id or 'global'}:{state_key or 'state'}"

    @classmethod
    async def should_notify_transition(
        cls,
        user_id: str,
        source_type: str,
        source_id: str | None,
        state_key: str | None,
        current_state_value: str | None,
        redis_client: Any = None,
    ) -> bool:
        """Evaluate if state has changed or if notification should be sent.

        Returns True if:
        - No state tracking requested (current_state_value is None)
        - State has transitioned from previous value to a new value
        - First time state is observed

        Returns False if:
        - State is identical to previously alerted state (in cooldown)
        """
        if current_state_value is None:
            return True

        key = cls.make_state_key(user_id, source_type, source_id, state_key)

        prev_state: str | None = None
        if redis_client is not None:
            try:
                cached = await redis_client.get(f"proactive:state:{key}")
                if cached:
                    prev_state = cached.decode("utf-8") if isinstance(cached, bytes) else str(cached)
            except Exception as exc:
                logger.debug("Redis state get failed, falling back to local cache: %s", exc)
                prev_state = _LOCAL_STATE_CACHE.get(key)
        else:
            prev_state = _LOCAL_STATE_CACHE.get(key)

        if prev_state == current_state_value:
            logger.info(
                "Cooldown active: unchanged state '%s' for %s. Suppressing notification.",
                current_state_value,
                key,
            )
            return False

        # Transition detected! Update recorded state
        logger.info(
            "State transition for %s: '%s' -> '%s'",
            key,
            prev_state,
            current_state_value,
        )
        if redis_client is not None:
            try:
                # Store with 7-day TTL
                await redis_client.setex(f"proactive:state:{key}", 60 * 60 * 24 * 7, current_state_value)
            except Exception as exc:
                logger.debug("Redis state set failed: %s", exc)
        _LOCAL_STATE_CACHE[key] = current_state_value

        return True

    @classmethod
    def reset_local_cache(cls) -> None:
        """Clear in-memory state transitions (useful for tests)."""
        _LOCAL_STATE_CACHE.clear()
