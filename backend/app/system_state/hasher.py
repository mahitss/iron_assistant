"""Deterministic canonical state hashing for snapshot fingerprinting and change detection (Task 93 Phase 6).

Invariants:
- Deterministic: identical operational states always yield identical hashes.
- Discriminative: meaningful status/health/topology changes alter the hash.
- Independent of dict iteration order and non-operational volatile timestamps.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.system_state.models import StateEdge, StateEntity

# Volatile metadata keys that must not affect operational state equivalence
EXCLUDED_METADATA_KEYS = {
    "transient_timestamp",
    "stale_detected_at",
    "last_polled",
    "ephemeral_token",
    "nonce",
    "trace_id",
}


def _canonical_entity_repr(entity: StateEntity) -> dict[str, Any]:
    """Extract canonical operational attributes of an entity, excluding volatile fields."""
    filtered_meta = {
        k: str(v)
        for k, v in sorted(entity.metadata.items())
        if k not in EXCLUDED_METADATA_KEYS and not k.startswith("_")
    }
    return {
        "id": entity.id,
        "type": entity.state_type.value,
        "status": entity.status.value,
        "epistemic": entity.epistemic_status.value,
        "confidence": round(float(entity.confidence), 4),
        "health": round(float(entity.health_score), 4),
        "meta": filtered_meta,
    }


def _canonical_edge_repr(edge: StateEdge) -> dict[str, Any]:
    """Extract canonical operational attributes of an edge."""
    return {
        "source": edge.source_id,
        "target": edge.target_id,
        "edge_type": edge.edge_type.value,
        "epistemic": edge.epistemic_status.value,
        "weight": round(float(edge.weight), 4),
    }


def compute_state_hash(entities: dict[str, StateEntity], edges: list[StateEdge]) -> str:
    """Compute a SHA-256 fingerprint representing the operational topology and health.

    Returns string with format: 'ssh_<64_hex_chars>'
    """
    sorted_entity_keys = sorted(entities.keys())
    canonical_entities = [_canonical_entity_repr(entities[k]) for k in sorted_entity_keys]

    canonical_edges = sorted(
        [_canonical_edge_repr(e) for e in edges],
        key=lambda x: (x["source"], x["target"], x["edge_type"]),
    )

    payload = {
        "entities": canonical_entities,
        "edges": canonical_edges,
    }

    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"ssh_{digest}"
