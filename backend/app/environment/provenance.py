"""Provenance tracking and observation idempotency for Environment Intelligence (Task 54)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.environment.temporal import utc_now


def generate_observation_id(source: str, resource_canonical_id: str, payload: dict[str, Any]) -> str:
    """Generates an idempotent observation ID based on source, resource, and normalized content."""
    raw = json.dumps(payload, sort_keys=True, default=str)
    h = hashlib.sha256(f"{source}:{resource_canonical_id}:{raw}".encode("utf-8")).hexdigest()[:16]
    return f"obs_{h}"


def build_provenance(
    source: str,
    collector: str = "kairo_env_collector",
    method: str = "api_pull",
    observation_id: str | None = None,
    verified_by: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Constructs a standard provenance dictionary."""
    prov = {
        "source": source,
        "collector": collector,
        "method": method,
        "observed_at": utc_now().isoformat(),
        "observation_id": observation_id or f"obs_{hashlib.sha256(str(utc_now().timestamp()).encode()).hexdigest()[:12]}",
    }
    if verified_by:
        prov["verified_by"] = verified_by
        prov["verified_at"] = utc_now().isoformat()
    if extra:
        prov.update(extra)
    return prov
