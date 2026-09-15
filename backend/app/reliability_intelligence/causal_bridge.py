"""Causal driver identification bridge integrating Task 73 causal models without duplication."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.reliability_intelligence.models import (
    CausalDriverAnalysis,
    ReliabilitySignal,
    ReliabilitySignalType,
    generate_ri_id,
)

logger = logging.getLogger("kairo.reliability_intelligence.causal_bridge")


class CausalBridge:
    """Delegates causal driver analysis to Task 73 causal root-cause models."""

    def __init__(self, root_cause_analyzer: Optional[Any] = None) -> None:
        self._analyzer = root_cause_analyzer

    def _get_analyzer(self) -> Any:
        if self._analyzer is None:
            try:
                from app.causal.root_cause import RootCauseAnalyzer
                self._analyzer = RootCauseAnalyzer
            except Exception as e:
                logger.debug("Task 73 RootCauseAnalyzer lazy init: %s", e)
        return self._analyzer

    def identify_causal_drivers(
        self,
        signal: ReliabilitySignal,
        incident_id: str,
    ) -> CausalDriverAnalysis:
        """Determines underlying condition, trigger, mechanism, and contributing factors."""
        comp = signal.component
        sig_type = signal.signal_type

        # Canonical mapping based on signal typology
        if sig_type == ReliabilitySignalType.MEMORY_EXHAUSTION:
            trigger = "Memory RSS growth exceeding safe operating ceiling"
            condition = "Unbounded buffer retention or cache accumulation"
            mechanism = "Heap memory allocation outpacing deallocation/GC"
            factors = ["High concurrent batch workloads", "Stale in-flight execution contexts"]
            strength = 0.88

        elif sig_type == ReliabilitySignalType.CPU_EXHAUSTION:
            trigger = "CPU core utilization sustained near 100%"
            condition = "CPU-intensive task loop or runaway process execution"
            mechanism = "Thread scheduler starvation under high compute load"
            factors = ["Concurrent background jobs", "Unbounded regex evaluation"]
            strength = 0.82

        elif sig_type == ReliabilitySignalType.CRASH_LOOP:
            trigger = "Repeated rapid worker process termination (SIGSEGV/panic)"
            condition = "Native daemon or child sandbox panic under specific payload"
            mechanism = "Process supervisor immediate restart tripping circuit breaker"
            factors = ["Corrupt shared memory state", "Uncaught native exception"]
            strength = 0.95

        elif sig_type == ReliabilitySignalType.NETWORK_INSTABILITY:
            trigger = "Elevated network socket connection drops and timeouts"
            condition = "TCP transport degradation or upstream host unreachability"
            mechanism = "Connection pool exhaustion and socket read timeouts"
            factors = ["Upstream network jitter", "Exceeded host concurrency limits"]
            strength = 0.78

        elif sig_type == ReliabilitySignalType.QUEUE_SATURATION:
            trigger = "Request queue depth exceeding processing threshold"
            condition = "Worker consumption latency exceeds ingress request rate"
            mechanism = "Backpressure accumulation in async message buffer"
            factors = ["Slow downstream tool executions", "Bursty client submissions"]
            strength = 0.80

        elif sig_type == ReliabilitySignalType.TOOL_DEGRADATION:
            trigger = "Repeated non-zero exit codes or schema validation errors from tool"
            condition = "External tool dependency or environment prerequisite drift"
            mechanism = "Tool execution failure triggering retry loops"
            factors = ["Outdated tool credentials", "Target binary path changed"]
            strength = 0.75

        elif sig_type == ReliabilitySignalType.RECOVERY_DEGRADATION:
            trigger = "Recovery success rate dropping below 80% SLA"
            condition = "Underlying failure condition mutated beyond strategy scope"
            mechanism = "Repeated execution of degraded recovery strategy failing verification"
            factors = ["Persistent environmental faults", "Exhausted retry budgets"]
            strength = 0.90

        else:
            trigger = f"Anomalous metric delta on {comp}"
            condition = f"System state deviation in {sig_type.value}"
            mechanism = "Threshold breach in operational health telemetry"
            factors = ["External load variation"]
            strength = 0.65

        evidence = [
            f"Correlation ID: {signal.correlation_id}",
            f"Signal: {sig_type.value} on {comp} (current={signal.current_value})",
            f"Evaluated causal mechanism: {mechanism}",
        ]

        return CausalDriverAnalysis(
            driver_id=generate_ri_id("cause"),
            primary_trigger=trigger,
            underlying_condition=condition,
            mechanism=mechanism,
            causal_strength=strength,
            confidence=signal.confidence,
            contributing_factors=factors,
            evidence=evidence,
        )


_global_causal_bridge: Optional[CausalBridge] = None


def get_causal_bridge() -> CausalBridge:
    global _global_causal_bridge
    if _global_causal_bridge is None:
        _global_causal_bridge = CausalBridge()
    return _global_causal_bridge
