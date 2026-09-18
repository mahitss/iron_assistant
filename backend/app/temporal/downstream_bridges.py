"""Downstream Bridges for Task 111:
Integration adapters connecting Temporal Intelligence to Context, Attention,
Missions, Decisions, Actions, and Situation Awareness.

Strict Invariants:
- TEMPORAL INTELLIGENCE CANNOT AUTHORIZE ACTIONS
- TEMPORAL ANOMALY != PRIORITY AUTHORITY
- HISTORICAL APPROVAL != CURRENT APPROVAL
- NO-ACTION CASES MUST BE EXPLICITLY SUPPORTED
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.temporal.domain import (
    AttributionCertainty,
    ChangeSet,
    ChangeSummary,
    ExpectedVsActual,
    StateTransition,
    TemporalAnomaly,
    TemporalEvent,
    TemporalGap,
    utc_now,
)
from app.temporal.diff_engine import DiffEngine


class DownstreamTemporalBridges:
    """Bridges temporal signals and diffs into existing cognitive subsystems."""

    @classmethod
    def format_for_context_working_set(
        cls,
        changeset: ChangeSet,
        gaps: List[TemporalGap],
        anomalies: List[TemporalAnomaly],
        max_items: int = 5,
    ) -> Dict[str, Any]:
        """Provides a bounded structured payload for Task 110 Cognitive Working Set."""
        summary = DiffEngine.generate_summary(changeset)

        recent_changes_payload = [
            {
                "entity_id": c.entity_id,
                "attribute": c.attribute_path,
                "category": c.category.value,
                "from": str(c.previous_value),
                "to": str(c.new_value),
                "attribution": c.attribution.value,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in changeset.changes[:max_items]
        ]

        critical_gaps_payload = [
            {
                "subsystem": g.subsystem,
                "duration_seconds": g.duration_seconds,
                "reason": g.reason,
            }
            for g in gaps[:max_items]
        ]

        return {
            "summary_headline": summary.headline,
            "total_changes": summary.total_changes,
            "has_degraded_capabilities": summary.has_degraded_capabilities,
            "has_unattributed_changes": summary.has_unattributed_changes,
            "recent_changes": recent_changes_payload,
            "unresolved_gaps": critical_gaps_payload,
            "anomaly_count": len(anomalies),
            "temporal_coverage_verified": len(gaps) == 0,
        }

    @classmethod
    def format_attention_signals(
        cls,
        anomalies: List[TemporalAnomaly],
        changeset: ChangeSet,
    ) -> List[Dict[str, Any]]:
        """Extracts salience signals for Task 109 Attention without assuming priority authority."""
        signals = []

        # Oscillation signal
        oscillations = [a for a in anomalies if a.anomaly_type.value == "RAPID_OSCILLATION"]
        if oscillations:
            signals.append({
                "signal_type": "TEMPORAL_RAPID_OSCILLATION",
                "entity_id": oscillations[0].entity_id,
                "urgency_boost": 0.3,
                "importance_boost": 0.4,
                "description": oscillations[0].explanation,
            })

        # Degraded capability change signal
        if changeset.degraded_count > 0:
            signals.append({
                "signal_type": "TEMPORAL_CAPABILITY_DEGRADATION",
                "urgency_boost": 0.4,
                "importance_boost": 0.5,
                "description": f"{changeset.degraded_count} entities transitioned to degraded state.",
            })

        return signals

    @classmethod
    def evaluate_no_action_recommendation(
        cls,
        changeset: ChangeSet,
        gaps: List[TemporalGap],
        is_emergency_stop_active: bool = False,
    ) -> Tuple[bool, str]:
        """Evaluates whether current temporal conditions recommend NO_ACTION."""
        if is_emergency_stop_active:
            return True, "EmergencyStop is active. All action execution blocked."

        if len(changeset.changes) == 0:
            return True, "No temporal state changes detected. No action required."

        # If all changes are informational or recovered
        if changeset.degraded_count == 0 and changeset.modified_count == 0 and changeset.removed_count == 0:
            return True, "Only benign/recovery changes observed. No intervention needed."

        # If a critical offline gap exists where state is completely uncertain
        critical_offline = [g for g in gaps if g.is_offline_period]
        if critical_offline:
            return True, f"Critical unobserved gap ({critical_offline[0].duration_seconds:.1f}s). State uncertain until validated."

        return False, "Actionable changes present."
