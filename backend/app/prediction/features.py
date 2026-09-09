"""Feature Engineering, Chronological Splits, and Anti-Future-Leakage Guards (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kairo.prediction.features")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DataLeakageError(Exception):
    """Raised when future temporal information is detected in historical prediction features (Spec 171)."""


@dataclass
class FeatureSnapshot:
    """Historical telemetry feature vector strictly bounded by a cutoff timestamp (Spec 170-174)."""

    cutoff_timestamp: datetime
    features: Dict[str, Any]
    source_provenance: Dict[str, str] = field(default_factory=dict)
    is_missing_critical: bool = False
    feature_count: int = 0
    is_stale: bool = False

    def get_feature(self, name: str, default: Any = None) -> Any:
        return self.features.get(name, default)


class FeaturePipeline:
    """Extracts features strictly respecting temporal boundaries without future leakage (Spec 170-175)."""

    @classmethod
    def build_features(
        cls,
        raw_telemetry: List[Dict[str, Any]],
        cutoff_time: datetime,
        required_keys: Optional[List[str]] = None,
    ) -> FeatureSnapshot:
        """Enforce Spec 170, 171: Use chronological evaluation. Future information must NEVER enter features."""
        extracted: Dict[str, Any] = {}
        provenance: Dict[str, str] = {}

        for record in raw_telemetry:
            rec_time = record.get("timestamp")
            if isinstance(rec_time, str):
                rec_time = datetime.fromisoformat(rec_time)

            if rec_time and rec_time > cutoff_time:
                # Future information detected! (Spec 171)
                raise DataLeakageError(
                    f"Temporal leakage violation: record at {rec_time.isoformat()} is after cutoff {cutoff_time.isoformat()}"
                )

            for k, v in record.items():
                if k != "timestamp":
                    extracted[k] = v
                    provenance[k] = record.get("source_id", "telemetry")

        missing_critical = False
        if required_keys:
            missing_critical = any(req not in extracted for req in required_keys)

        return FeatureSnapshot(
            cutoff_timestamp=cutoff_time,
            features=extracted,
            source_provenance=provenance,
            is_missing_critical=missing_critical,
            feature_count=len(extracted),
            is_stale=False,
        )

    @classmethod
    def extract_snapshot(
        cls,
        points: List[Dict[str, Any]],
        as_of_time: datetime,
    ) -> FeatureSnapshot:
        """Extract snapshot respecting as_of_time cutoff boundary (Spec 170-172)."""
        for pt in points:
            t = pt.get("timestamp")
            if isinstance(t, str):
                t = datetime.fromisoformat(t)
            if t and t > as_of_time:
                raise DataLeakageError(
                    f"Data leakage detected: telemetry timestamp {t.isoformat()} > cutoff {as_of_time.isoformat()} (Spec 171)."
                )

        features = {f"point_{i}": pt for i, pt in enumerate(points)}
        return FeatureSnapshot(
            cutoff_timestamp=as_of_time,
            features=features,
            feature_count=len(points),
            is_stale=False,
        )
