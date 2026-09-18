"""Multi-dimensional Epistemic Uncertainty Quantification for Task 114.
Assesses uncertainty across 15 explicit dimensions without fabricating certainty or treating missing data as false.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.observation.domain import (
    UncertaintyDimension,
    UncertaintyDimensionType,
    UncertaintyLevel,
    UncertaintyState,
    utc_now,
)


class EpistemicUncertaintyEngine:
    """Evaluates epistemic uncertainty across 15 distinct dimensions (Section 7)."""

    @classmethod
    def evaluate_uncertainty(
        cls,
        target_entity: str,
        observed_signals: Optional[Dict[str, Any]] = None,
        context_items: Optional[List[Dict[str, Any]]] = None,
        assumptions: Optional[List[str]] = None,
        stale_threshold_seconds: float = 60.0,
    ) -> UncertaintyState:
        observed_signals = observed_signals or {}
        context_items = context_items or []
        assumptions = assumptions or []

        dimensions: Dict[str, UncertaintyDimension] = {}
        missing_data_count = 0
        stale_signals_count = 0

        # Assess each of the 15 dimensions
        for dim_type in UncertaintyDimensionType:
            key = dim_type.value.lower()
            sig = observed_signals.get(key) or observed_signals.get(dim_type.value)

            if sig is None:
                missing_data_count += 1
                # Invariant: UNKNOWN != FALSE
                dimensions[dim_type.value] = UncertaintyDimension(
                    dimension=dim_type,
                    level=UncertaintyLevel.UNKNOWN,
                    confidence=0.2,
                    description=f"No direct observations or telemetry for dimension '{dim_type.value}'.",
                    evidence_count=0,
                    is_critical=dim_type in {
                        UncertaintyDimensionType.STATE,
                        UncertaintyDimensionType.CAPABILITY,
                        UncertaintyDimensionType.CAUSAL,
                        UncertaintyDimensionType.DECISION,
                    },
                )
            else:
                staleness = float(sig.get("staleness_seconds", 0.0))
                conf = float(sig.get("confidence", 0.8))
                status_str = str(sig.get("status", "KNOWN")).upper()

                if staleness > stale_threshold_seconds:
                    stale_signals_count += 1
                    level = UncertaintyLevel.STALE
                    conf = max(0.1, conf * 0.5)
                    desc = f"Signal for '{dim_type.value}' is stale ({staleness:.1f}s old > {stale_threshold_seconds:.1f}s threshold)."
                elif status_str in {l.value for l in UncertaintyLevel}:
                    level = UncertaintyLevel(status_str)
                    desc = sig.get("description", f"Dimension '{dim_type.value}' assessed as {level.value}.")
                else:
                    level = UncertaintyLevel.KNOWN if conf >= 0.8 else UncertaintyLevel.LIKELY
                    desc = sig.get("description", f"Dimension '{dim_type.value}' active.")

                dimensions[dim_type.value] = UncertaintyDimension(
                    dimension=dim_type,
                    level=level,
                    confidence=min(1.0, max(0.0, conf)),
                    description=desc,
                    evidence_count=int(sig.get("evidence_count", 1)),
                    staleness_seconds=staleness,
                    is_critical=bool(sig.get("is_critical", False)),
                )

        # Invariant: MODEL CONFIDENCE != REALITY; compute overall confidence with penalties
        known_count = sum(1 for d in dimensions.values() if d.level == UncertaintyLevel.KNOWN)
        likely_count = sum(1 for d in dimensions.values() if d.level == UncertaintyLevel.LIKELY)
        unknown_count = sum(1 for d in dimensions.values() if d.level in {UncertaintyLevel.UNKNOWN, UncertaintyLevel.UNCERTAIN})

        base_conf = (known_count * 1.0 + likely_count * 0.75 + unknown_count * 0.2) / len(UncertaintyDimensionType)
        penalty = min(0.4, (missing_data_count * 0.02) + (stale_signals_count * 0.05) + (len(assumptions) * 0.03))
        overall_conf = round(max(0.1, min(1.0, base_conf - penalty)), 2)

        return UncertaintyState(
            target_entity=target_entity,
            overall_confidence=overall_conf,
            dimensions=dimensions,
            assumptions_count=len(assumptions),
            stale_signals_count=stale_signals_count,
            missing_data_count=missing_data_count,
            assessed_at=utc_now(),
        )

    @classmethod
    def compute_uncertainty_delta(
        cls,
        before: UncertaintyState,
        after: UncertaintyState,
    ) -> float:
        """Measure net uncertainty reduction (0.0 to 1.0). Positive means confidence improved."""
        return max(0.0, round(after.overall_confidence - before.overall_confidence, 3))
