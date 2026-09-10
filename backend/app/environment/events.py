"""Raw Environment Event Ingestion and Normalization (Task 54, Prompts #84, #85)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.environment.provenance import build_provenance, generate_observation_id
from app.environment.temporal import utc_now


class NormalizedEnvironmentEvent(BaseModel):
    event_id: str
    source: str
    resource_id: str
    event_type: str
    payload: dict[str, Any]
    observed_at: str
    provenance: dict[str, Any]


class EnvironmentEventManager:
    """Ingests raw environmental events, normalizes structure, and prevents duplicate processing."""

    def __init__(self) -> None:
        self._processed_observation_ids: set[str] = set()

    def process_raw_event(
        self,
        source: str,
        resource_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> NormalizedEnvironmentEvent | None:
        """Normalizes and deduplicates raw observation events."""
        obs_id = generate_observation_id(source, resource_id, payload)

        # Prompt #84, #85: Idempotency and duplicate prevention
        if obs_id in self._processed_observation_ids:
            return None  # Duplicate event ignored

        self._processed_observation_ids.add(obs_id)
        if len(self._processed_observation_ids) > 10000:
            # Simple eviction of oldest half
            self._processed_observation_ids = set(list(self._processed_observation_ids)[5000:])

        now = utc_now()
        prov = build_provenance(source=source, observation_id=obs_id)
        return NormalizedEnvironmentEvent(
            event_id=f"ev_{obs_id}",
            source=source,
            resource_id=resource_id,
            event_type=event_type,
            payload=payload,
            observed_at=now.isoformat(),
            provenance=prov,
        )
