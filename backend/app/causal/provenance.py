"""Provenance tracking and evidence hashing for Causal Reasoning (Task 55, Prompts #99, #140)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.causal.temporal import utc_now


def generate_evidence_id(evidence_type: str, source: str, observation: dict[str, Any]) -> str:
    """Generates an idempotent evidence identifier based on content hash."""
    raw = json.dumps(observation, sort_keys=True, default=str)
    h = hashlib.sha256(f"{evidence_type}:{source}:{raw}".encode("utf-8")).hexdigest()[:12]
    return f"ev_{h}"


def build_causal_provenance(
    source: str,
    method: str = "observational_inference",
    evidence_ids: list[str] | None = None,
    verified_by: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Constructs an authoritative audit provenance dictionary for causal records."""
    now = utc_now()
    prov = {
        "source": source,
        "method": method,
        "created_at": now.isoformat(),
        "evidence_refs": evidence_ids or [],
    }
    if verified_by:
        prov["verified_by"] = verified_by
        prov["verified_at"] = now.isoformat()
    if extra:
        prov.update(extra)
    return prov
