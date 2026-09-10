"""Observation grounding and anti-false-observation controls (INVARIANTS 85, 86)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


class FalseObservationError(Exception):
    """Raised when an environmental observation is asserted without Perception evidence."""
    pass


class ObservationTracker:
    """Ensures environmental observations are strictly backed by empirical perception telemetry."""

    def __init__(self) -> None:
        # list of verified observation records
        self._verified_observations: List[Dict[str, Any]] = []

    def record_observation(
        self,
        target: str,
        observation: str,
        perception_evidence: Dict[str, Any],
        sensor_type: str = "PERCEPTION_ENGINE",
    ) -> Dict[str, Any]:
        """INVARIANT 85: Never claim environmental observation without Perception evidence."""
        if not perception_evidence:
            raise FalseObservationError(
                f"Cannot assert observation '{observation}' on '{target}' without empirical perception telemetry."
            )

        rec = {
            "target": target,
            "observation": observation.strip(),
            "evidence": perception_evidence,
            "sensor_type": sensor_type,
            "is_prediction": False,  # INVARIANT 86: Predictions are never observations
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._verified_observations.append(rec)
        return rec

    def has_observation_evidence(self, target: str) -> bool:
        return any(o["target"].lower() == target.lower() for o in self._verified_observations)
