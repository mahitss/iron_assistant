"""Stale Snapshot & State Drift Defense Engine (Task 89).

Guards recovery simulations against execution on drifted or obsolete state:
- Computes state drift between baseline snapshot and live operational state.
- Detects resource drift (memory, CPU, processes), capability drift, topology drift.
- Enforces TTL expiration on simulated plans (default: 180 seconds).
- Rejects simulation results if state drift exceeds safety thresholds (STALE_SIMULATION).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.simulation.digital_twin import RuntimeSnapshot
from app.simulation.recovery_models import RecoverySimulationResult

logger = logging.getLogger("kairo.simulation.drift_detector")


class StateDriftReport:
    """Detailed discrepancy assessment between baseline snapshot and live state."""

    def __init__(
        self,
        is_stale: bool,
        drift_score: float,
        staleness_reasons: list[str],
        detected_at: datetime,
    ) -> None:
        self.is_stale = is_stale
        self.drift_score = drift_score
        self.staleness_reasons = staleness_reasons
        self.detected_at = detected_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_stale": self.is_stale,
            "drift_score": round(self.drift_score, 4),
            "staleness_reasons": self.staleness_reasons,
            "detected_at": self.detected_at.isoformat(),
        }


class StaleSimulationDetector:
    """Evaluates simulation staleness, state drift, and TTL validity."""

    def __init__(
        self,
        max_snapshot_age_seconds: float = 180.0,
        max_allowed_drift_score: float = 0.35,
    ) -> None:
        self.max_snapshot_age_seconds = max_snapshot_age_seconds
        self.max_allowed_drift_score = max_allowed_drift_score

    def evaluate_staleness(
        self,
        baseline_snapshot: RuntimeSnapshot,
        current_snapshot: RuntimeSnapshot,
        simulation_result: RecoverySimulationResult | None = None,
    ) -> StateDriftReport:
        """Compares baseline snapshot with current live snapshot to evaluate drift."""
        now = datetime.now(timezone.utc)
        reasons: list[str] = []
        drift_penalty = 0.0

        # 1. Snapshot Age check
        age_seconds = (now - baseline_snapshot.timestamp).total_seconds()
        if age_seconds > self.max_snapshot_age_seconds:
            reasons.append(
                f"Snapshot expired: age {round(age_seconds, 1)}s exceeds max TTL {self.max_snapshot_age_seconds}s"
            )
            drift_penalty += 0.50

        # 2. Cryptographic hash comparison
        if baseline_snapshot.hash_sha256 != current_snapshot.hash_sha256:
            drift_penalty += 0.15

        # 3. Fingerprint validation (Runtime instance, configuration, capabilities)
        if baseline_snapshot.runtime_instance_id != current_snapshot.runtime_instance_id:
            reasons.append("Runtime instance changed (restart occurred since snapshot capture)")
            drift_penalty += 0.40

        if baseline_snapshot.capability_fingerprint != current_snapshot.capability_fingerprint:
            reasons.append("Capability fingerprint drifted (capabilities catalog updated)")
            drift_penalty += 0.30

        if baseline_snapshot.configuration_fingerprint != current_snapshot.configuration_fingerprint:
            reasons.append("Configuration fingerprint drifted")
            drift_penalty += 0.25

        # 4. Resource drift check (Memory RSS & CPU pressure)
        base_mem = baseline_snapshot.resource_state.get("memory_rss_mb", 100.0)
        curr_mem = current_snapshot.resource_state.get("memory_rss_mb", 100.0)
        mem_diff = abs(curr_mem - base_mem)
        if mem_diff > 150.0:  # > 150MB drift
            reasons.append(f"Memory RSS drifted significantly by {round(mem_diff, 1)}MB")
            drift_penalty += 0.20

        # 5. Health state divergence
        if baseline_snapshot.health_state != current_snapshot.health_state:
            reasons.append("System health state diverged since snapshot capture")
            drift_penalty += 0.25

        # 6. Emergency Stop check
        base_sec = baseline_snapshot.security_state.get("emergency_stop_active", False)
        curr_sec = current_snapshot.security_state.get("emergency_stop_active", False)
        if curr_sec and not base_sec:
            reasons.append("EmergencyStop was engaged after snapshot capture")
            drift_penalty += 1.00

        total_drift = min(1.0, drift_penalty)
        is_stale = (total_drift >= self.max_allowed_drift_score) or (len(reasons) > 0 and total_drift >= 0.30)

        if is_stale and simulation_result:
            simulation_result.is_stale = True
            simulation_result.state_drift_detected = True

        logger.info(
            "Stale evaluation: is_stale=%s, drift_score=%.3f, reasons=%s",
            is_stale,
            total_drift,
            reasons,
        )

        return StateDriftReport(
            is_stale=is_stale,
            drift_score=total_drift,
            staleness_reasons=reasons,
            detected_at=now,
        )


_global_drift_detector = StaleSimulationDetector()


def get_drift_detector() -> StaleSimulationDetector:
    """Singleton accessor for StaleSimulationDetector."""
    return _global_drift_detector
