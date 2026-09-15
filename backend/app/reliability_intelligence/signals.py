"""Early warning state machine, anti-flapping hysteresis, and signal deduplication for Task 90."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set

from app.reliability_intelligence.models import (
    EarlyWarningState,
    ReliabilitySignal,
    ReliabilitySignalType,
    generate_ri_id,
    _now_utc,
)

logger = logging.getLogger("kairo.reliability_intelligence.signals")

# Explicit deterministic progression order
STATE_RANK: Dict[EarlyWarningState, int] = {
    EarlyWarningState.NORMAL: 0,
    EarlyWarningState.WATCH: 1,
    EarlyWarningState.ELEVATED: 2,
    EarlyWarningState.HIGH: 3,
    EarlyWarningState.CRITICAL: 4,
    EarlyWarningState.IMMINENT: 5,
}


class SignalStateMachine:
    """Manages early-warning state progression with anti-flapping hysteresis."""

    def __init__(self, escalation_consecutive_required: int = 1, deescalation_consecutive_required: int = 3) -> None:
        self.escalation_req = escalation_consecutive_required
        self.deescalation_req = deescalation_consecutive_required
        # component -> current state
        self._states: Dict[str, EarlyWarningState] = defaultdict(lambda: EarlyWarningState.NORMAL)
        # component -> count of pending state readings
        self._pending_readings: Dict[str, Tuple[EarlyWarningState, int]] = {}

    def get_state(self, component: str) -> EarlyWarningState:
        return self._states[component.lower()]

    def transition(self, component: str, candidate_state: EarlyWarningState) -> Tuple[EarlyWarningState, bool]:
        """Evaluates candidate state with hysteresis and transitions if stable."""
        comp = component.lower()
        current = self._states[comp]

        if candidate_state == current:
            self._pending_readings.pop(comp, None)
            return current, False

        curr_rank = STATE_RANK[current]
        cand_rank = STATE_RANK[candidate_state]

        # Check pending counts
        pending_state, count = self._pending_readings.get(comp, (candidate_state, 0))
        if pending_state != candidate_state:
            pending_state = candidate_state
            count = 0

        count += 1
        self._pending_readings[comp] = (pending_state, count)

        # Escalation requires fewer readings for rapid safety response
        threshold = self.escalation_req if cand_rank > curr_rank else self.deescalation_req

        if count >= threshold:
            self._states[comp] = candidate_state
            self._pending_readings.pop(comp, None)
            logger.info("EarlyWarning state transition for %s: %s -> %s", comp, current.value, candidate_state.value)
            return candidate_state, True

        return current, False


class SignalCorrelator:
    """Correlates multiple multi-source telemetry signals to prevent alarm fatigue."""

    def __init__(self, correlation_window_seconds: float = 60.0) -> None:
        self.window_sec = correlation_window_seconds
        # Active recent signals: correlation_key -> list of ReliabilitySignal
        self._recent_signals: Dict[str, List[ReliabilitySignal]] = defaultdict(list)

    def _make_key(self, component: str, signal_type: ReliabilitySignalType) -> str:
        # Group related resource signals together
        comp = component.lower()
        if signal_type in (
            ReliabilitySignalType.RESOURCE_PRESSURE,
            ReliabilitySignalType.MEMORY_EXHAUSTION,
            ReliabilitySignalType.CPU_EXHAUSTION,
            ReliabilitySignalType.DISK_EXHAUSTION,
        ):
            return f"{comp}:resource_exhaustion"
        elif signal_type in (
            ReliabilitySignalType.LATENCY_DEGRADATION,
            ReliabilitySignalType.QUEUE_SATURATION,
            ReliabilitySignalType.CONNECTION_EXHAUSTION,
        ):
            return f"{comp}:throughput_bottleneck"
        elif signal_type in (
            ReliabilitySignalType.NETWORK_INSTABILITY,
            ReliabilitySignalType.PROTOCOL_INSTABILITY,
        ):
            return f"{comp}:network_link"
        return f"{comp}:{signal_type.value}"

    def ingest_signal(self, signal: ReliabilitySignal) -> Tuple[str, bool]:
        """Ingests signal and returns (correlation_id, is_new_incident)."""
        now = _now_utc()
        cutoff = now.timestamp() - self.window_sec
        key = self._make_key(signal.component, signal.signal_type)

        # Prune expired
        self._recent_signals[key] = [s for s in self._recent_signals[key] if s.timestamp.timestamp() >= cutoff]

        existing = self._recent_signals[key]
        if existing:
            # Re-use existing correlation ID
            corr_id = existing[0].correlation_id
            signal.correlation_id = corr_id
            existing.append(signal)
            return corr_id, False
        else:
            corr_id = signal.correlation_id or generate_ri_id("corr")
            signal.correlation_id = corr_id
            self._recent_signals[key].append(signal)
            return corr_id, True


_global_state_machine: Optional[SignalStateMachine] = None
_global_correlator: Optional[SignalCorrelator] = None


def get_signal_state_machine() -> SignalStateMachine:
    global _global_state_machine
    if _global_state_machine is None:
        _global_state_machine = SignalStateMachine()
    return _global_state_machine


def get_signal_correlator() -> SignalCorrelator:
    global _global_correlator
    if _global_correlator is None:
        _global_correlator = SignalCorrelator()
    return _global_correlator
