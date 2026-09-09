"""State drift detection and external reality observation (Task 39, Spec 125-134, 179-185)."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.state.schemas import (
    DriftSeverity,
    ObservationFreshness,
    StateDrift,
)

logger = logging.getLogger("kairo.state.drift")


class DriftDetector:
    """Detects discrepancies between desired state and observed external reality."""

    @classmethod
    def evaluate_external_observation(
        cls,
        resource: str,
        is_source_reachable: bool,
        observed_data: Any | None,
        observed_at: datetime | None,
        max_freshness_seconds: float = 300.0,
    ) -> tuple[ObservationFreshness, Any | None]:
        """Evaluates observation freshness according to external system reachability (Specs 181-183).
        
        Invariants:
        1. If external source is unreachable -> UNKNOWN, never guess healthy or failed.
        2. If observation is older than threshold -> STALE.
        3. If fresh and reachable -> CURRENT.
        """
        if not is_source_reachable:
            logger.warning("External source for '%s' is unreachable; marking UNKNOWN", resource)
            return ObservationFreshness.UNKNOWN, observed_data

        if observed_at is None:
            return ObservationFreshness.UNKNOWN, observed_data

        now = datetime.now(UTC)
        age_seconds = (now - observed_at).total_seconds()
        if age_seconds > max_freshness_seconds:
            logger.info("Observation for '%s' is %.1fs old; marking STALE", resource, age_seconds)
            return ObservationFreshness.STALE, observed_data

        return ObservationFreshness.CURRENT, observed_data

    @classmethod
    def detect_drift(
        cls,
        resource: str,
        desired_state: Any,
        observed_state: Any,
        freshness: ObservationFreshness = ObservationFreshness.CURRENT,
    ) -> StateDrift | None:
        """Detects drift between desired state and observed real-world state (Spec 127).
        
        Invariant: Drift detection does NOT authorize remediation. Remediation must
        be governed by Intent, Policy, and Approvals.
        """
        if freshness == ObservationFreshness.UNKNOWN:
            # Cannot accurately evaluate drift against an unknown source
            return StateDrift(
                resource=resource,
                desired=desired_state,
                observed="UNKNOWN",
                detected_at=datetime.now(UTC),
                severity=DriftSeverity.HIGH,
                classification="ERRONEOUS",
            )

        if desired_state != observed_state:
            # Determine severity based on types
            severity = DriftSeverity.HIGH if freshness == ObservationFreshness.STALE else DriftSeverity.MEDIUM
            drift = StateDrift(
                resource=resource,
                desired=desired_state,
                observed=observed_state,
                detected_at=datetime.now(UTC),
                severity=severity,
                classification="TEMPORARY" if freshness == ObservationFreshness.CURRENT else "ERRONEOUS",
            )
            logger.warning(
                "State drift detected on '%s': desired=%s, observed=%s",
                resource,
                desired_state,
                observed_state,
            )
            return drift

        return None
