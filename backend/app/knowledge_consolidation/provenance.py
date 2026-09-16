"""Lineage and provenance management for KAIRO knowledge (Task 92 Phase 3).

Guarantees:
- Every retained knowledge item has auditable provenance
- Never represents model output as automatically factual
- Distinguishes observed, inferred, derived, model-generated, external, user-asserted, and system-verified
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import MemoryProvenance, ProvenanceSourceType


class ProvenanceTracker:
    """Manages creation, linking, and audit trails for knowledge provenance."""

    def __init__(self) -> None:
        self._provenances: dict[str, MemoryProvenance] = {}

    def create_provenance(
        self,
        memory_id: str,
        source_type: ProvenanceSourceType = ProvenanceSourceType.OBSERVED,
        source_identifier: str | None = None,
        conversation_id: str | None = None,
        message_id: str | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
        event_id: str | None = None,
        document_ref: str | None = None,
        external_source_ref: str | None = None,
        extraction_method: str = "direct",
        actor: str = "kairo_system",
    ) -> MemoryProvenance:
        """Create and register a strongly typed provenance record."""
        prov = MemoryProvenance(
            memory_id=memory_id,
            source_type=source_type,
            source_identifier=source_identifier,
            conversation_id=conversation_id,
            message_id=message_id,
            task_id=task_id,
            run_id=run_id,
            event_id=event_id,
            document_ref=document_ref,
            external_source_ref=external_source_ref,
            extraction_method=extraction_method,
            extracted_at=datetime.now(UTC),
            validation_status="VERIFIED" if source_type == ProvenanceSourceType.SYSTEM_VERIFIED else "UNVERIFIED",
            actor=actor,
        )
        self._provenances[prov.provenance_id] = prov
        return prov

    def record_transformation(
        self,
        provenance_id: str,
        transformation_type: str,
        details: dict[str, Any],
        actor: str = "kairo_system",
    ) -> None:
        """Record an auditable transformation step (e.g. normalization, consolidation, deduction)."""
        prov = self._provenances.get(provenance_id)
        if prov:
            prov.transformation_history.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "transformation": transformation_type,
                    "details": details,
                    "actor": actor,
                }
            )

    def get_provenance(self, provenance_id: str) -> MemoryProvenance | None:
        """Retrieve a provenance record by ID."""
        return self._provenances.get(provenance_id)

    def get_by_memory_id(self, memory_id: str) -> MemoryProvenance | None:
        """Retrieve the primary provenance record for a given memory ID."""
        for prov in self._provenances.values():
            if prov.memory_id == memory_id:
                return prov
        return None
