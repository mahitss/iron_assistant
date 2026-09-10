"""Observation Ingestion, Temporal Ordering, and Correlation Tracking (Task 55, Prompts #6, #7, #25)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.causal.schemas import CausalRelationshipType
from app.causal.temporal import calculate_temporal_distance_seconds, is_temporally_prior, utc_now


class ObservationRecord(BaseModel):
    observation_id: str
    entity: str
    metric_name: str
    value: Any
    timestamp: datetime = Field(default_factory=utc_now)
    source: str


class ObservationCorrelator:
    """Detects temporal precedence and statistical correlations without asserting causation."""

    @staticmethod
    def evaluate_temporal_order(obs_a: ObservationRecord, obs_b: ObservationRecord) -> dict[str, Any]:
        """Prompt #7, #8: Analyzes whether A preceded B without asserting causality."""
        a_first = is_temporally_prior(obs_a.timestamp, obs_b.timestamp)
        distance = calculate_temporal_distance_seconds(obs_a.timestamp, obs_b.timestamp)
        return {
            "a_preceded_b": a_first,
            "b_preceded_a": not a_first and obs_a.timestamp != obs_b.timestamp,
            "simultaneous": obs_a.timestamp == obs_b.timestamp,
            "distance_seconds": distance,
            "relationship": CausalRelationshipType.TEMPORALLY_PRECEDES if a_first else CausalRelationshipType.CORRELATES_WITH,
            "causality_established": False,  # Prompt #8: Temporal order alone cannot establish causality
        }

    @staticmethod
    def detect_preceding_changes(
        target_incident_time: datetime | str,
        recent_changes: list[dict[str, Any]],
        window_seconds: int = 1800,  # 30 mins
    ) -> list[dict[str, Any]]:
        """Prompt #25: Identifies changes occurring immediately prior to an incident."""
        preceding = []
        for chg in recent_changes:
            chg_time = chg.get("timestamp")
            if chg_time and is_temporally_prior(chg_time, target_incident_time):
                dist = calculate_temporal_distance_seconds(chg_time, target_incident_time)
                if dist <= window_seconds:
                    preceding.append({
                        "change": chg,
                        "seconds_before_incident": dist,
                        "temporal_proximity": "IMMEDIATE" if dist <= 300 else "NEAR",
                    })
        preceding.sort(key=lambda x: x["seconds_before_incident"])
        return preceding


class ObservationIngestor:
    """Ingests raw observations and generates standardized observation records."""

    @staticmethod
    def ingest_observation(
        entity: str,
        variable: str,
        value: Any,
        source: str = "telemetry",
    ) -> dict[str, Any]:
        """Ingest and standardize an entity-variable observation."""
        return {
            "entity": entity,
            "variable": variable,
            "value": value,
            "source": source,
            "timestamp": utc_now().isoformat(),
        }

