"""Provenance recording, source references, and lineage tracking (INVARIANTS 15, 16, 17)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.schemas import ProvenanceType


class ProvenanceRecorder:
    """Manages immutable audit provenance for graph nodes, edges, decisions, and assertions."""

    def __init__(self) -> None:
        self._audit_log: List[Dict[str, Any]] = []

    def record_provenance(
        self,
        entity_id: str,
        provenance_type: ProvenanceType,
        source_reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """INVARIANT 17: Store source reference rather than unnecessary raw source content."""
        record = {
            "record_id": str(uuid.uuid4()),
            "entity_id": entity_id,
            "provenance_type": provenance_type.value,
            "source_reference": source_reference,
            "metadata": metadata or {},
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
        }
        self._audit_log.append(record)
        return record

    def get_audit_trail(self, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if entity_id:
            return [r for r in self._audit_log if r["entity_id"] == entity_id]
        return list(self._audit_log)
