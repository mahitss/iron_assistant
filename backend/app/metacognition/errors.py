"""Error memory, transient error decay, pattern detection, and escalation (INVARIANTS 158-163)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional


class ErrorMemoryManager:
    """Manages error logs, transient error decay, and repeated failure pattern detection without panic."""

    def __init__(self, decay_hours: int = 24) -> None:
        self._error_history: List[Dict[str, Any]] = []
        self.decay_threshold = timedelta(hours=decay_hours)

    def record_error(
        self,
        component: str,
        error_message: str,
        is_transient: bool = True,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """INVARIANT 158: Stores errors with component provenance."""
        now = datetime.now(UTC)
        rec = {
            "component": component,
            "error_message": error_message,
            "is_transient": is_transient,
            "provenance": provenance or {},
            "timestamp": now,
            "resolved": False,
        }
        self._error_history.append(rec)
        return rec

    def mark_recovered(self, component: str) -> None:
        """INVARIANT 160: Successful recovery updates error state."""
        for e in self._error_history:
            if e["component"] == component and not e["resolved"]:
                e["resolved"] = True

    def get_active_error_count(self, component: str) -> int:
        """INVARIANT 159: Old transient errors decay and do not permanently degrade capability."""
        now = datetime.now(UTC)
        active = [
            e for e in self._error_history
            if e["component"] == component
            and not e["resolved"]
            and (now - e["timestamp"] < self.decay_threshold)
        ]
        return len(active)

    def detect_failure_pattern(self, component: str, threshold: int = 3) -> Dict[str, Any]:
        """INVARIANT 161 & 162: Detects repeated failures and triggers escalation if threshold reached."""
        count = self.get_active_error_count(component)
        is_pattern = count >= threshold
        return {
            "component": component,
            "recent_failures_count": count,
            "is_repeated_pattern": is_pattern,
            "escalation_required": is_pattern,
            "recommendation": "Pause automated tool retries and request operator review" if is_pattern else "Normal operational state",
        }
