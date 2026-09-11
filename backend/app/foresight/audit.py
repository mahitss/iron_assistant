"""Append-only cryptographic SHA-256 hash-chained audit trail for World Model & Foresight Engine (Task 65, Spec 84)."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuditRecord(BaseModel):
    """Immutable audit record in the cryptographic hash chain."""

    model_config = ConfigDict(extra="ignore")

    record_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=_now_utc)
    event_type: str  # ENTITY_CREATED, STATE_TRANSITION, FORECAST_GENERATED, SCENARIO_BRANCHED, EARLY_WARNING, REASSESSMENT
    actor: str = "system"
    tenant_id: str = "default"
    details: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = "0" * 64
    record_hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this record including previous_hash."""
        payload = {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor": self.actor,
            "tenant_id": self.tenant_id,
            "details": self.details,
            "previous_hash": self.previous_hash,
        }
        canonical_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()


class ForesightAuditor:
    """Manages an append-only, tamper-evident audit trail for world model evolutions."""

    def __init__(self) -> None:
        self._chain: list[AuditRecord] = []
        self._latest_hash: str = "0" * 64

    def record_event(
        self,
        event_type: str,
        details: dict[str, Any],
        actor: str = "system",
        tenant_id: str = "default",
    ) -> AuditRecord:
        """Record a world model change or foresight action into the hash chain."""
        rec = AuditRecord(
            event_type=event_type,
            actor=actor,
            tenant_id=tenant_id,
            details=details,
            previous_hash=self._latest_hash,
        )
        rec.record_hash = rec.compute_hash()
        self._latest_hash = rec.record_hash
        self._chain.append(rec)
        logger.info(
            "FORESIGHT_AUDIT_RECORDED: id=%s type=%s hash=%s",
            rec.record_id,
            rec.event_type,
            rec.record_hash[:8],
        )
        return rec

    def verify_integrity(self) -> bool:
        """Verify unbroken cryptographic integrity of the audit chain."""
        expected_prev = "0" * 64
        for i, rec in enumerate(self._chain):
            if rec.previous_hash != expected_prev:
                logger.error(
                    "AUDIT_CHAIN_BROKEN: index=%d record_id=%s expected_prev=%s actual_prev=%s",
                    i,
                    rec.record_id,
                    expected_prev,
                    rec.previous_hash,
                )
                return False
            recomputed = rec.compute_hash()
            if rec.record_hash != recomputed:
                logger.error(
                    "AUDIT_HASH_TAMPERED: index=%d record_id=%s stored=%s recomputed=%s",
                    i,
                    rec.record_id,
                    rec.record_hash,
                    recomputed,
                )
                return False
            expected_prev = rec.record_hash
        return True

    def get_audit_trail(
        self,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Retrieve recent audit records with optional tenant filter."""
        records = self._chain
        if tenant_id and tenant_id != "default":
            records = [r for r in records if r.tenant_id == tenant_id]
        return records[-limit:]

    def clear(self) -> None:
        """Reset the audit chain (used for testing)."""
        self._chain.clear()
        self._latest_hash = "0" * 64


foresight_auditor = ForesightAuditor()
