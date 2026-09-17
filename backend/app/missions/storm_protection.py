"""Mission Storm Protection, Circuit Breakers & Anti-Loop Defense (Task 100)."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    Mission,
    MissionHealth,
    MissionStatus,
)

logger = logging.getLogger("kairo.missions.storm_protection")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionStormError(RuntimeError):
    """Raised when an autonomous replan or intervention loop is tripped by circuit breaker."""
    pass


class MissionStormDefense:
    """Detects and arrests infinite mission loops (situation -> replan -> fail -> situation).

    Invariants:
    - Bounded replanning attempts within sliding time windows.
    - Consecutive action/milestone failures trip circuit breaker to AWAITING_USER.
    - Requires human intervention or cooldown to reset tripped breakers.
    """

    def __init__(
        self,
        max_replans_per_window: int = 4,
        window_seconds: float = 600.0,
        max_consecutive_failures: int = 3,
        min_replan_cooldown_seconds: float = 10.0,
    ) -> None:
        self.max_replans_per_window = max_replans_per_window
        self.window_seconds = window_seconds
        self.max_consecutive_failures = max_consecutive_failures
        self.min_replan_cooldown_seconds = min_replan_cooldown_seconds

        # Internal tracking per mission_id
        self._replan_history: dict[str, list[datetime]] = defaultdict(list)
        self._failure_streak: dict[str, int] = defaultdict(int)
        self._tripped_circuits: dict[str, dict[str, Any]] = {}

    def check_can_replan(self, mission: Mission) -> tuple[bool, str | None]:
        """Check whether the mission is permitted to initiate a replanning cycle."""
        m_id = mission.mission_id
        now = _now_utc()

        # 1. Check if circuit is already tripped
        if m_id in self._tripped_circuits:
            reason = self._tripped_circuits[m_id]["reason"]
            return False, f"Circuit breaker tripped: {reason}. Human intervention required."

        # 2. Check consecutive failure streak
        if self._failure_streak[m_id] >= self.max_consecutive_failures:
            self.trip_circuit(
                mission,
                reason=f"Exceeded maximum consecutive failure threshold ({self.max_consecutive_failures})",
            )
            return False, "Circuit breaker tripped due to consecutive failures."

        # 3. Check sliding window replan rate
        history = self._replan_history[m_id]
        recent = [t for t in history if (now - t).total_seconds() <= self.window_seconds]
        self._replan_history[m_id] = recent

        if len(recent) >= self.max_replans_per_window:
            self.trip_circuit(
                mission,
                reason=f"Exceeded maximum replan velocity ({len(recent)} replans in {self.window_seconds}s)",
            )
            return False, "Circuit breaker tripped due to replan velocity storm."

        # 4. Check minimum cooldown between replans
        if recent:
            elapsed_since_last = (now - recent[-1]).total_seconds()
            if elapsed_since_last < self.min_replan_cooldown_seconds:
                return False, f"Replanning in cooldown. Please wait {self.min_replan_cooldown_seconds - elapsed_since_last:.1f}s."

        return True, None

    def record_replan(self, mission: Mission) -> None:
        """Record an authorized replanning event."""
        can_proceed, err = self.check_can_replan(mission)
        if not can_proceed:
            raise MissionStormError(err or "Replanning prohibited by storm defense")

        self._replan_history[mission.mission_id].append(_now_utc())
        logger.info("Recorded replan for mission %s (recent count: %d)", mission.mission_id, len(self._replan_history[mission.mission_id]))

    def record_failure(self, mission: Mission, reason: str = "") -> None:
        """Record an operational failure towards the failure streak."""
        m_id = mission.mission_id
        self._failure_streak[m_id] += 1
        streak = self._failure_streak[m_id]
        logger.warning("Mission %s operational failure recorded (streak=%d): %s", m_id, streak, reason)

        if streak >= self.max_consecutive_failures:
            self.trip_circuit(
                mission,
                reason=f"Operational failure streak reached {streak}: {reason}",
            )

    def record_success(self, mission: Mission) -> None:
        """Reset the consecutive failure streak upon verified operational success."""
        m_id = mission.mission_id
        if self._failure_streak[m_id] > 0:
            logger.info("Resetting failure streak for mission %s after verified success", m_id)
            self._failure_streak[m_id] = 0

    def trip_circuit(self, mission: Mission, reason: str) -> None:
        """Trip circuit breaker, halt autonomous progression, and transition to AWAITING_USER."""
        m_id = mission.mission_id
        self._tripped_circuits[m_id] = {
            "tripped_at": _now_utc(),
            "reason": reason,
        }

        mission.status = MissionStatus.AWAITING_USER
        mission.health = MissionHealth.BLOCKED
        mission.updated_at = _now_utc()

        logger.critical("MISSION_STORM_CIRCUIT_TRIPPED: mission=%s reason=%s", m_id, reason)

    def reset_circuit(self, mission: Mission) -> None:
        """Manually reset the circuit breaker after human review."""
        m_id = mission.mission_id
        if m_id in self._tripped_circuits:
            del self._tripped_circuits[m_id]
        self._failure_streak[m_id] = 0
        self._replan_history[m_id].clear()
        logger.info("Reset storm defense circuit breaker for mission %s", m_id)


# Global singleton instance
storm_defense = MissionStormDefense()
