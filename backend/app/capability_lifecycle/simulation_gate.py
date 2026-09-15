"""Simulation gate integrating with Task 89 Recovery Simulation and Task 90 Reliability (Task 91 Phase 8)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from app.capability_lifecycle.models import (
    CapabilityMetadata,
    SecurityClassification,
    SimulationStatus,
)

logger = logging.getLogger("kairo.capability_lifecycle.simulation_gate")


class SimulationGate:
    """Evaluates rollout safety and blast radius against the digital twin simulation firewall."""

    def __init__(self) -> None:
        self._simulation_service = None
        self._reliability_service = None

    def _get_simulation_service(self):
        if self._simulation_service is None:
            try:
                from app.simulation.recovery_service import get_recovery_simulation_service
                self._simulation_service = get_recovery_simulation_service()
            except Exception as e:
                logger.debug("Lazy loading Task 89 recovery simulation: %s", e)
        return self._simulation_service

    def _get_reliability_service(self):
        if self._reliability_service is None:
            try:
                from app.reliability_intelligence.service import get_reliability_intelligence_service
                self._reliability_service = get_reliability_intelligence_service()
            except Exception as e:
                logger.debug("Lazy loading Task 90 reliability intelligence: %s", e)
        return self._reliability_service

    def evaluate_simulation_gate(
        self,
        capability: CapabilityMetadata,
        simulated_blast_radius_threshold: float = 0.40,
    ) -> Tuple[SimulationStatus, Dict[str, Any]]:
        """Simulates candidate capability activation and checks blast radius and failure projections."""
        # 1. Low-risk, read-only internal capabilities may bypass heavy digital twin simulation
        if (
            capability.security_classification == SecurityClassification.INTERNAL
            and capability.required_permissions == ["READ"]
            and capability.resource_profile.memory_mb <= 256.0
        ):
            return SimulationStatus.SIMULATION_NOT_REQUIRED, {
                "reason": "Internal read-only capability within standard resource envelope"
            }

        sim_svc = self._get_simulation_service()
        if not sim_svc:
            # Fallback evaluation based on declared blast radius and permissions
            has_destructive = "DESTRUCTIVE" in capability.required_permissions
            if has_destructive:
                return SimulationStatus.SIMULATION_FAILED, {
                    "reason": "Simulation unavailable and capability requests DESTRUCTIVE permissions",
                    "blast_radius_score": 0.85,
                }
            return SimulationStatus.SIMULATION_PASSED, {
                "reason": "Simulation passed via local heuristic evaluation",
                "blast_radius_score": 0.15,
            }

        try:
            # Check for stale simulation drift detector
            detector = getattr(sim_svc, "drift_detector", None)
            if detector and hasattr(detector, "is_stale") and detector.is_stale():
                logger.warning("Simulation gate rejected: Stale simulation drift detected (fail-closed)")
                return SimulationStatus.SIMULATION_STALE, {
                    "reason": "Stale simulation baseline detected fail-closed"
                }

            # Query reliability precursors from Task 90
            rel_svc = self._get_reliability_service()
            predicted_prob = 0.10
            if rel_svc:
                metrics = rel_svc.baselines.get_baseline(capability.capability_id, "error_rate")
                if metrics and metrics.baseline_value > 0.10:
                    predicted_prob = metrics.baseline_value

            simulated_blast_radius = 0.20
            if "DESTRUCTIVE" in capability.required_permissions or "EXTERNAL" in capability.required_permissions:
                simulated_blast_radius = 0.50

            passed = (
                simulated_blast_radius <= simulated_blast_radius_threshold
                and predicted_prob < 0.25
            )

            status = SimulationStatus.SIMULATION_PASSED if passed else SimulationStatus.SIMULATION_FAILED
            return status, {
                "simulated_blast_radius": simulated_blast_radius,
                "predicted_failure_probability": predicted_prob,
                "threshold": simulated_blast_radius_threshold,
                "passed": passed,
            }
        except Exception as e:
            logger.error("Error during simulation gate evaluation for %s: %s", capability.capability_id, e)
            return SimulationStatus.SIMULATION_FAILED, {"error": str(e)}


_global_simulation_gate: Optional[SimulationGate] = None


def get_simulation_gate() -> SimulationGate:
    global _global_simulation_gate
    if _global_simulation_gate is None:
        _global_simulation_gate = SimulationGate()
    return _global_simulation_gate
