"""Provenance tracking and verifiable source linking for executive state claims (INVARIANTS 16, 23, 202)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid


class ExecutiveProvenanceTracker:
    """Attaches and audits verifiable provenance references for all executive assertions."""

    @classmethod
    def create_provenance(
        cls,
        source_system: str,
        source_id: str,
        actor: str = "kairo",
        proof_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 16 & 202: Generates traceable provenance payload."""
        return {
            "provenance_id": f"prv_{uuid.uuid4().hex[:12]}",
            "source_system": source_system,
            "source_id": source_id,
            "actor": actor,
            "proof_ref": proof_ref,
            "recorded_at": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }

    @classmethod
    def assert_provenance(cls, claim_name: str, provenance: dict[str, Any]) -> None:
        """INVARIANT 202: Asserts that an executive state claim references verifiable evidence."""
        if not provenance or not provenance.get("source_id"):
            raise ValueError(f"INVARIANT 202: State claim '{claim_name}' is missing source provenance.")
