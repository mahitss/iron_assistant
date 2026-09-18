"""Conflicting Multi-Source Observation Arbitration Engine for Task 114.
Manages divergent or contradictory observations across independent sensors without blind averaging.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.observation.domain import (
    ConflictResolutionStrategy,
    ObservationOutcome,
)

logger = logging.getLogger("kairo.observation.conflict_engine")


class ObservationConflictEngine:
    """Detects and arbitrates conflicts between independent observation sources (Section 40)."""

    @classmethod
    def evaluate_conflict(
        cls,
        new_outcome: ObservationOutcome,
        existing_outcomes: List[ObservationOutcome],
    ) -> Tuple[bool, str, ConflictResolutionStrategy]:
        """Detects whether incoming observation contradicts previously gathered evidence."""
        metric_new = new_outcome.data_payload.get("metric") or new_outcome.data_payload.get("status")
        val_new = new_outcome.data_payload.get("value")

        for prior in existing_outcomes:
            metric_prior = prior.data_payload.get("metric") or prior.data_payload.get("status")
            val_prior = prior.data_payload.get("value")

            # Check if measuring the same subject/metric from different sources
            if metric_new and metric_prior and metric_new == metric_prior:
                if str(val_new).lower() != str(val_prior).lower():
                    # Direct contradiction detected!
                    details = (
                        f"Conflict detected between source '{new_outcome.source}' (value: '{val_new}', conf: {new_outcome.confidence}) "
                        f"and prior source '{prior.source}' (value: '{val_prior}', conf: {prior.confidence}). "
                        f"Do NOT average blindly. Preserving both signals for epistemic arbitration."
                    )
                    logger.warning(details)

                    # Strategy selection based on provenance & freshness
                    if new_outcome.freshness_seconds < prior.freshness_seconds and new_outcome.confidence >= prior.confidence:
                        strategy = ConflictResolutionStrategy.RECENCY
                    elif new_outcome.confidence != prior.confidence:
                        strategy = ConflictResolutionStrategy.PROVENANCE_WEIGHT
                    else:
                        strategy = ConflictResolutionStrategy.UNRESOLVED

                    return True, details, strategy

        return False, "", ConflictResolutionStrategy.INDEPENDENT_CONFIRMATION
