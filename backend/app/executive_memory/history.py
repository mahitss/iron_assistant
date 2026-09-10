"""Attempt history, approach deduplication, and past outcome retrieval (INVARIANTS 94-98, 164)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid


class AttemptHistoryManager:
    """Answers 'What did we try already?' and links previous approaches to failure or success evidence."""

    def __init__(self) -> None:
        # attempt_id -> attempt dict
        self._attempts: dict[str, dict[str, Any]] = {}

    def record_attempt(
        self,
        problem_description: str,
        approach_taken: str,
        was_successful: bool,
        evidence: dict[str, Any] | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 94-98: Records an attempted approach with empirical outcome evidence."""
        aid = f"att_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        record = {
            "attempt_id": aid,
            "problem_description": problem_description.strip(),
            "approach_taken": approach_taken.strip(),
            "was_successful": was_successful,
            "evidence": evidence or {},
            "project_id": project_id,
            "timestamp": now.isoformat(),
        }
        self._attempts[aid] = record
        return record

    def list_previous_attempts(self, problem_description: str) -> list[dict[str, Any]]:
        """INVARIANT 95 & 96: Returns previous approaches tried for the given problem."""
        target = problem_description.lower().strip()
        return [
            a for a in self._attempts.values()
            if any(w in a["problem_description"].lower() for w in target.split() if len(w) > 3)
        ]

    def is_known_failure(self, approach_taken: str) -> tuple[bool, str | None]:
        """INVARIANT 164: Avoids repeating known failed approaches unless intentionally reconsidered."""
        appr_lower = approach_taken.lower().strip()
        for a in self._attempts.values():
            if not a["was_successful"] and appr_lower in a["approach_taken"].lower():
                return True, f"Approach previously failed: {a['approach_taken']} (Evidence: {a.get('evidence', {})})"
        return False, None
