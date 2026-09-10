"""Decision and task outcome tracking with Learning Engine integration (INVARIANTS 53-55)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid


class OutcomeHistoryTracker:
    """Maintains historical record of decision and task outcomes compared against initial expectations."""

    def __init__(self) -> None:
        # outcome_id -> outcome dict
        self._outcomes: dict[str, dict[str, Any]] = {}

    def record_outcome(
        self,
        target_id: str,
        target_type: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
        verified: bool = False,
        lesson_id: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 53-55: Records expected vs actual outcome and links to learned lessons."""
        oid = f"out_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        record = {
            "outcome_id": oid,
            "target_id": target_id,
            "target_type": target_type,
            "expected": expected,
            "actual": actual,
            "verified": verified,
            "lesson_id": lesson_id,
            "timestamp": now.isoformat(),
        }
        self._outcomes[oid] = record
        return record

    def list_outcomes(self, target_id: str | None = None) -> list[dict[str, Any]]:
        results = list(self._outcomes.values())
        if target_id:
            results = [o for o in results if o["target_id"] == target_id]
        return results
