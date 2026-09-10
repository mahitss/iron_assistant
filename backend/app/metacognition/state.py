"""Internal operational state model and runtime lifecycle tracker (INVARIANTS 38, 108-111)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


class InternalStateManager:
    """Tracks internal system state (planning, executing, idle, error) distinct from external world state."""

    def __init__(self) -> None:
        self.current_state: str = "IDLE"
        self.last_transition: datetime = datetime.now(UTC)
        self._state_history: List[Dict[str, Any]] = []

    def transition_to(self, new_state: str, reason: str = "lifecycle") -> str:
        valid_states = {"IDLE", "PLANNING", "EXECUTING", "WAITING", "REFLECTING", "ERROR"}
        if new_state not in valid_states:
            raise ValueError(f"Invalid internal state: '{new_state}'")

        now = datetime.now(UTC)
        self._state_history.append({
            "from_state": self.current_state,
            "to_state": new_state,
            "reason": reason,
            "timestamp": now.isoformat(),
        })
        self.current_state = new_state
        self.last_transition = now
        return self.current_state

    def get_state(self) -> str:
        return self.current_state
