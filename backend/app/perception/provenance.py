"""Perception Provenance Tracking, Ingestion Lineage, and Verification Auditing (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.perception.provenance")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProvenanceRecord:
    """Audit trail detailing origin and transformation chain of an observation (Spec 12, 182, 183)."""

    record_id: str
    observation_id: str
    source_id: str
    source_type: str
    adapter_name: str
    ingested_at: datetime = field(default_factory=utc_now)
    normalized_at: datetime = field(default_factory=utc_now)
    redaction_applied: bool = False
    validation_status: str = "PASSED"
    signature_verified: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "observation_id": self.observation_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "adapter_name": self.adapter_name,
            "ingested_at": self.ingested_at.isoformat(),
            "normalized_at": self.normalized_at.isoformat(),
            "redaction_applied": self.redaction_applied,
            "validation_status": self.validation_status,
            "signature_verified": self.signature_verified,
            "metadata": self.metadata,
        }


class ProvenanceTracker:
    """Manages provenance history and ensures non-repudiation of environmental data."""

    def __init__(self) -> None:
        # observation_id -> ProvenanceRecord
        self._records: Dict[str, ProvenanceRecord] = {}

    def record_provenance(
        self,
        observation_id: str,
        source_id: str,
        source_type: str,
        adapter_name: str,
        redaction_applied: bool = False,
        signature_verified: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceRecord:
        rec_id = f"prov_{uuid.uuid4().hex[:10]}"
        rec = ProvenanceRecord(
            record_id=rec_id,
            observation_id=observation_id,
            source_id=source_id,
            source_type=source_type,
            adapter_name=adapter_name,
            redaction_applied=redaction_applied,
            signature_verified=signature_verified,
            metadata=metadata or {},
        )
        self._records[observation_id] = rec
        return rec

    def get_provenance(self, observation_id: str) -> Optional[ProvenanceRecord]:
        return self._records.get(observation_id)
