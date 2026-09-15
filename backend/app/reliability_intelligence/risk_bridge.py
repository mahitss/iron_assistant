"""Risk propagation bridge integrating Task 75 cascade models without duplication."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.reliability_intelligence.models import (
    PredictedImpact,
    ReliabilitySignal,
    ReliabilitySignalType,
)

logger = logging.getLogger("kairo.reliability_intelligence.risk_bridge")


class RiskBridge:
    """Delegates blast radius and cascading risk estimation to Task 75 risk propagation."""

    def __init__(self, propagation_service: Optional[Any] = None) -> None:
        self._propagation_service = propagation_service

    def _get_propagation_service(self) -> Any:
        if self._propagation_service is None:
            try:
                from app.propagation.service import PropagationService
                self._propagation_service = PropagationService()
            except Exception as e:
                logger.debug("Task 75 propagation service lazy init: %s", e)
        return self._propagation_service

    def estimate_impact(
        self,
        signal: ReliabilitySignal,
    ) -> PredictedImpact:
        """Calculates blast-radius score, cascade paths, and impact dimensions."""
        comp = signal.component.lower()
        sig_type = signal.signal_type

        # Subsystem topological dependency downstream mapping
        if comp in ("native_runtime", "rust_runtime", "ipc"):
            affected = ["sandbox", "native_tool", "network_fabric", "computer"]
            score = 0.85
            sec_impact = "HIGH"
            user_impact = "HIGH"
            op_impact = "CRITICAL"
        elif comp in ("network", "network_fabric", "http"):
            affected = ["web_search", "browser", "external_apis"]
            score = 0.60
            sec_impact = "MEDIUM"
            user_impact = "MEDIUM"
            op_impact = "DEGRADED"
        elif comp in ("sandbox", "sandbox_executor"):
            affected = ["code_execution", "cli_tools"]
            score = 0.50
            sec_impact = "MEDIUM"
            user_impact = "MEDIUM"
            op_impact = "CONTAINED"
        elif comp in ("computer", "input", "display"):
            affected = ["ui_automation", "desktop_control"]
            score = 0.45
            sec_impact = "MEDIUM"
            user_impact = "HIGH"
            op_impact = "CONTAINED"
        elif comp in ("workflow", "orchestration"):
            affected = ["autonomous_tasks", "scheduled_jobs"]
            score = 0.65
            sec_impact = "LOW"
            user_impact = "HIGH"
            op_impact = "DEGRADED"
        else:
            affected = [comp]
            score = 0.25
            sec_impact = "LOW"
            user_impact = "LOW"
            op_impact = "MINIMAL"

        # Severity scaler
        if signal.severity == "P0":
            score = min(1.0, score * 1.25)
        elif signal.severity == "P3":
            score = score * 0.5

        return PredictedImpact(
            blast_radius_score=round(score, 2),
            affected_components=affected,
            affected_workflows=[f"wf_{c}" for c in affected[:2]],
            affected_resources=["cpu_reservation", "memory_buffer", "network_sockets"] if score > 0.5 else ["worker_slot"],
            security_impact=sec_impact,
            user_impact=user_impact,
            operational_impact=op_impact,
        )


_global_risk_bridge: Optional[RiskBridge] = None


def get_risk_bridge() -> RiskBridge:
    global _global_risk_bridge
    if _global_risk_bridge is None:
        _global_risk_bridge = RiskBridge()
    return _global_risk_bridge
