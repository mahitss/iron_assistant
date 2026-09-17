"""Bounded Shared Task-State, Evidence Blackboard, and Typed Agent Communication (Phase 17 & 18).

Invariants:
- The blackboard is BOUNDED (max entries per session = 500).
- It is NOT a second memory system.
- Facts must indicate validation status.
- Messages are typed, source-attributed, and audited.
"""

from __future__ import annotations

from collections import defaultdict
import threading
from typing import Any

from app.swarm.orchestration_domain import (
    AgentMessage,
    BlackboardEntry,
    MessageType,
    _now_utc,
)


class BoundedBlackboard:
    """Thread-safe bounded shared task-state and typed messaging fabric for a swarm session."""

    def __init__(self, session_id: str = "default_session", max_entries: int = 500) -> None:
        self.session_id = session_id
        self.max_entries = max_entries
        self._lock = threading.RLock()
        self._entries: dict[str, BlackboardEntry] = {}
        self._messages: list[AgentMessage] = []
        self._agent_inboxes: dict[str, list[AgentMessage]] = defaultdict(list)
        self._counter = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def post(
        self,
        key: str = "",
        value: Any = None,
        author_agent_id: str = "anonymous",
        topic: str | None = None,
        content: Any = None,
        evidence_refs: list[str] | None = None,
        is_validated: bool = False,
    ) -> BlackboardEntry:
        """Write or update a blackboard fact with provenance."""
        with self._lock:
            self._counter += 1
            effective_key = key
            if not effective_key:
                effective_key = f"{topic or 'fact'}:{self._counter}"
            effective_val = content if content is not None else value

            if len(self._entries) >= self.max_entries and effective_key not in self._entries:
                # Evict oldest entry
                oldest_key = min(self._entries.keys(), key=lambda k: self._entries[k].created_at)
                del self._entries[oldest_key]

            entry = BlackboardEntry(
                session_id=self.session_id,
                key=effective_key,
                value=effective_val,
                author_agent_id=author_agent_id,
                evidence_refs=evidence_refs or [],
                is_validated=is_validated,
            )
            self._entries[effective_key] = entry
            return entry

    def query(self, topic: str | None = None) -> list[BlackboardEntry]:
        """Query entries, optionally filtered by topic prefix."""
        with self._lock:
            if not topic:
                return list(self._entries.values())
            prefix = f"{topic}:"
            return [e for e in self._entries.values() if e.key.startswith(prefix)]

    def get(self, key: str) -> BlackboardEntry | None:
        with self._lock:
            return self._entries.get(key)

    def validate_entry(self, key: str) -> bool:
        """Mark an entry as empirically validated."""
        with self._lock:
            if key in self._entries:
                self._entries[key].is_validated = True
                self._entries[key].updated_at = _now_utc()
                return True
            return False

    def list_entries(self) -> list[BlackboardEntry]:
        with self._lock:
            return list(self._entries.values())

    def send_message(self, message: AgentMessage) -> None:
        """Route typed message to recipient agent."""
        with self._lock:
            self._messages.append(message)
            self._agent_inboxes[message.recipient_id].append(message)

    def receive_messages(self, recipient_id: str) -> list[AgentMessage]:
        """Fetch pending messages for an agent."""
        with self._lock:
            msgs = list(self._agent_inboxes[recipient_id])
            self._agent_inboxes[recipient_id].clear()
            return msgs

    def get_all_messages(self) -> list[AgentMessage]:
        with self._lock:
            return list(self._messages)
