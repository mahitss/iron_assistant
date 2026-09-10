"""Commitments integration from communication and interpersonal interactions (INVARIANTS 63 & 64)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid


class CommitmentTracker:
    """Tracks verified commitments agreed upon across communication channels."""

    def __init__(self) -> None:
        # commitment_id -> commitment dict
        self._commitments: dict[str, dict[str, Any]] = {}

    def record_commitment(
        self,
        description: str,
        counterparty: str,
        due_at: datetime | None = None,
        source_message_id: str | None = None,
        status: str = "PENDING",
    ) -> dict[str, Any]:
        """INVARIANT 63 & 64: Records explicit commitment."""
        cid = f"com_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        record = {
            "commitment_id": cid,
            "description": description.strip(),
            "counterparty": counterparty,
            "due_at": due_at.isoformat() if due_at else None,
            "source_message_id": source_message_id,
            "status": status,
            "created_at": now.isoformat(),
        }
        self._commitments[cid] = record
        return record

    def list_pending_commitments(self) -> list[dict[str, Any]]:
        return [c for c in self._commitments.values() if c["status"] == "PENDING"]
