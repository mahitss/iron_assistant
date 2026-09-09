"""Version tracking and snapshot diffs for facts, decisions, and preferences."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid


class VersionManager:
    """Maintains immutable historical versions of decisions, preferences, and entity metadata."""

    def __init__(self) -> None:
        # entity_id -> list of version snapshots
        self._versions: Dict[str, List[Dict[str, Any]]] = {}

    def record_version(
        self,
        entity_id: str,
        snapshot: Dict[str, Any],
        reason: str,
        author: str = "system",
    ) -> Dict[str, Any]:
        """INVARIANT 104 & 105: Records version snapshot with timestamp, author, and reason."""
        record = {
            "version_id": str(uuid.uuid4()),
            "entity_id": entity_id,
            "version_number": len(self._versions.get(entity_id, [])) + 1,
            "snapshot": snapshot,
            "reason": reason,
            "author": author,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._versions.setdefault(entity_id, []).append(record)
        return record

    def get_version_history(self, entity_id: str) -> List[Dict[str, Any]]:
        return list(self._versions.get(entity_id, []))
