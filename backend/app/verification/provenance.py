"""Provenance chain and lineage tracking for Kairo Truth Engine (Task 42)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProvenanceNode(BaseModel):
    """An individual hop in an evidence provenance lineage."""

    model_config = ConfigDict(extra="ignore")

    node_id: str = Field(default_factory=lambda: f"prv_{uuid.uuid4().hex[:10]}")
    source_type: str = "direct"
    source_ref: str = "system"
    actor: str = "system"
    method: str = "DIRECT_CHECK"
    action: str = "observed"
    evidence_ref: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "source": self.source_ref,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "actor": self.actor,
            "method": self.method,
            "action": self.action,
            "evidence_ref": self.evidence_ref,
            "timestamp": self.timestamp.isoformat(),
            "checksum": self.checksum,
        }


# Alias for ProvenanceStep
ProvenanceStep = ProvenanceNode


class ProvenanceChain(BaseModel):
    """Complete traceable lineage of a verified claim (Spec 16, 17)."""

    model_config = ConfigDict(extra="ignore")

    claim_id: str
    nodes: list[ProvenanceNode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    def add_hop(self, source_type: str, source_ref: str, method: str = "DIRECT_CHECK", checksum: str | None = None) -> None:
        """Append an empirical observation to the provenance chain."""
        node = ProvenanceNode(
            source_type=source_type,
            source_ref=source_ref,
            method=method,
            checksum=checksum,
        )
        self.nodes.append(node)

    def add_step(
        self,
        action: str,
        source: str = "system",
        evidence_ref: str | None = None,
        method: str = "DIRECT_CHECK",
    ) -> None:
        """Append a step to the provenance chain."""
        node = ProvenanceNode(
            action=action,
            source_ref=source,
            evidence_ref=evidence_ref,
            method=method,
        )
        self.nodes.append(node)

    def get_summary(self) -> list[dict[str, Any]]:
        """Return a user-inspectable provenance audit summary."""
        return [
            {
                "source": n.source_ref,
                "type": n.source_type,
                "method": n.method,
                "action": n.action,
                "evidence_ref": n.evidence_ref,
                "timestamp": n.timestamp.isoformat(),
            }
            for n in self.nodes
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "steps": [n.to_dict() for n in self.nodes],
            "created_at": self.created_at.isoformat(),
        }
