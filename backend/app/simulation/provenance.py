"""Provenance tracking for simulation runs, model versions, and environmental snapshots."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SimulationProvenance(BaseModel):
    """Cryptographic and operational provenance metadata for simulation artifacts."""

    provenance_id: str = Field(default_factory=lambda: f"prov_{uuid.uuid4().hex[:12]}")
    simulation_id: str
    source_snapshot_id: str
    scenario_id: str
    model_name: str = "kairo_simulation_engine"
    model_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    creator: str = "kairo_autonomous_supervisor"
    state_fingerprint: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def generate_provenance(
    simulation_id: str,
    source_snapshot_id: str,
    scenario_id: str,
    initial_state: dict[str, Any],
    creator: str = "kairo_autonomous_supervisor",
) -> SimulationProvenance:
    """Generates an immutable provenance record with fingerprint for a simulation."""
    import json
    canonical = json.dumps(initial_state, sort_keys=True, default=str)
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return SimulationProvenance(
        simulation_id=simulation_id,
        source_snapshot_id=source_snapshot_id,
        scenario_id=scenario_id,
        creator=creator,
        state_fingerprint=fingerprint,
    )
