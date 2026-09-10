"""Metacognitive lineage, snapshot auditing, and provenance tracking (INVARIANTS 21, 97, 179)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid


class MetacognitiveProvenanceTracker:
    """Tracks audit lineage for self-model snapshots, capability adjustments, and reflections."""

    def __init__(self) -> None:
        # list of audit records
        self._audit_log: List[Dict[str, Any]] = []

    def record_event(
        self,
        event_type: str,
        entity_id: str,
        details: Dict[str, Any],
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """INVARIANT 179: Audits self-model changes, capability changes, and corrections."""
        rec = {
            "audit_id": str(uuid.uuid4()),
            "event_type": event_type,
            "entity_id": entity_id,
            "details": details,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._audit_log.append(rec)
        return rec

    def get_audit_trail(self, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if entity_id:
            return [e for e in self._audit_log if e["entity_id"] == entity_id]
        return list(self._audit_log)
