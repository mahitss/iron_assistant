"""Reconstruction Engine for Task 111:
Detects temporal anomalies, surfaces unobserved gaps, and performs offline catch-up reconstruction.

Strict Invariants:
- ABSENCE OF EVENT != PROOF OF ABSENCE
- RECONSTRUCTION != CERTAINTY
- OFFLINE GAPS DO NOT ASSUME STABILITY
- HISTORICAL STATE CANNOT AUTHORIZE CURRENT ACTIONS
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.temporal.domain import (
    ChangeSet,
    StateTransition,
    TemporalAnomaly,
    TemporalAnomalyType,
    TemporalEvent,
    TemporalGap,
    TemporalWatermark,
    gen_temporal_id,
    utc_now,
)
from app.temporal.diff_engine import DiffEngine


class ReconstructionEngine:
    """Detects timing anomalies, surfaces temporal gaps, and reconciles offline periods."""

    FUTURE_TOLERANCE_SECONDS = 30.0  # Events > 30s in future flagged
    OSCILLATION_WINDOW_SECONDS = 60.0  # 60s window for rapid switching detection
    OSCILLATION_THRESHOLD = 3         # >= 3 switches in 60s is oscillation

    @classmethod
    def detect_anomalies(
        cls,
        events: List[TemporalEvent],
        transitions: Optional[List[StateTransition]] = None,
        now_reference: Optional[datetime] = None,
    ) -> List[TemporalAnomaly]:
        """Scans events and transitions for temporal anomalies."""
        now = now_reference or utc_now()
        anomalies: List[TemporalAnomaly] = []

        # 1. Future-dated events
        for e in events:
            if (e.clocks.event_time - now).total_seconds() > cls.FUTURE_TOLERANCE_SECONDS:
                diff = (e.clocks.event_time - now).total_seconds()
                anomalies.append(
                    TemporalAnomaly(
                        anomaly_type=TemporalAnomalyType.FUTURE_DATED_EVENT,
                        entity_id=e.source_entity_id,
                        event_ids=[e.canonical_event_id],
                        severity="WARNING",
                        explanation=f"Event {e.canonical_event_id} timestamped {diff:.1f}s into the future.",
                        is_adversarial_suspect=e.is_untrusted,
                    )
                )

        # 2. Rapid oscillation detection in transitions
        if transitions:
            entity_transitions: Dict[str, List[StateTransition]] = {}
            for t in transitions:
                entity_transitions.setdefault(t.entity_id, []).append(t)

            for ent_id, t_list in entity_transitions.items():
                if len(t_list) >= cls.OSCILLATION_THRESHOLD:
                    # Sort transitions
                    t_list.sort(key=lambda t: t.timestamp)
                    for i in range(len(t_list) - cls.OSCILLATION_THRESHOLD + 1):
                        window = (t_list[i + cls.OSCILLATION_THRESHOLD - 1].timestamp - t_list[i].timestamp).total_seconds()
                        if window <= cls.OSCILLATION_WINDOW_SECONDS:
                            states = [t.next_state for t in t_list[i : i + cls.OSCILLATION_THRESHOLD]]
                            anomalies.append(
                                TemporalAnomaly(
                                    anomaly_type=TemporalAnomalyType.RAPID_OSCILLATION,
                                    entity_id=ent_id,
                                    event_ids=[t.trigger_event_id for t in t_list[i : i + cls.OSCILLATION_THRESHOLD] if t.trigger_event_id],
                                    severity="ERROR",
                                    explanation=f"Rapid state oscillation on entity '{ent_id}' across {states} in {window:.1f}s.",
                                    remediation_suggested="Apply hysteresis filter or stabilize actuator feedback loop.",
                                )
                            )
                            break

        return anomalies

    @classmethod
    def detect_temporal_gaps(
        cls,
        events: List[TemporalEvent],
        expected_heartbeat_seconds: float = 300.0,
        subsystem: str = "telemetry",
    ) -> List[TemporalGap]:
        """Detects periods where telemetry was completely absent."""
        if len(events) < 2:
            return []

        sorted_events = sorted(events, key=lambda e: e.clocks.event_time)
        gaps: List[TemporalGap] = []

        for i in range(len(sorted_events) - 1):
            e_current = sorted_events[i]
            e_next = sorted_events[i + 1]

            duration = (e_next.clocks.event_time - e_current.clocks.event_time).total_seconds()
            if duration > expected_heartbeat_seconds:
                gaps.append(
                    TemporalGap(
                        subsystem=subsystem,
                        entity_id=e_current.source_entity_id,
                        gap_start=e_current.clocks.event_time,
                        gap_end=e_next.clocks.event_time,
                        duration_seconds=duration,
                        reason=f"Silent telemetry window of {duration:.1f}s exceeding expected heartbeat {expected_heartbeat_seconds}s.",
                        is_offline_period=duration > 1800.0,  # > 30m considered offline period
                    )
                )

        return gaps

    @classmethod
    def reconcile_offline_period(
        cls,
        last_watermark: TemporalWatermark,
        reconnect_time: datetime,
        recovered_events: List[TemporalEvent],
        prior_state: Dict[str, Any],
        observed_current_state: Dict[str, Any],
    ) -> Tuple[ChangeSet, List[TemporalGap]]:
        """Reconciles state when returning online after a disconnection period."""
        # 1. Detect offline gap
        offline_duration = max(0.0, (reconnect_time - last_watermark.ingestion_watermark).total_seconds())
        gaps: List[TemporalGap] = []
        if offline_duration > 60.0:
            gaps.append(
                TemporalGap(
                    subsystem=last_watermark.subsystem,
                    gap_start=last_watermark.ingestion_watermark,
                    gap_end=reconnect_time,
                    duration_seconds=offline_duration,
                    reason=f"Offline disconnection window for {offline_duration:.1f}s.",
                    is_offline_period=True,
                )
            )

        # 2. Compute diff between state before disconnection and state upon reconnection
        changeset = DiffEngine.compute_diff(
            state_a=prior_state,
            state_b=observed_current_state,
            from_reference=f"watermark_{last_watermark.subsystem}",
            to_reference="reconnect_state",
            from_time=last_watermark.ingestion_watermark,
            to_time=reconnect_time,
        )

        # 3. Advance watermark
        last_watermark.ingestion_watermark = reconnect_time
        last_watermark.processing_watermark = reconnect_time
        last_watermark.reconciliation_watermark = reconnect_time
        last_watermark.last_updated = reconnect_time

        return changeset, gaps
