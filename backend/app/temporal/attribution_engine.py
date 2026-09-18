"""Attribution Engine for Task 111:
Evaluates causal links and Expected vs Actual discrepancies without fabrication.

Strict Invariants:
- EVENT != CAUSE
- TEMPORAL ORDER != CAUSATION
- CORRELATION != CAUSATION
- EXPECTED STATE != ACTUAL STATE
- UNATTRIBUTED CHANGE MUST REMAIN UNATTRIBUTED
- NEVER FABRICATE CAUSAL EXPLANATIONS
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.causal.temporal_engine import TemporalCausalityEngine
from app.temporal.domain import (
    AttributionCertainty,
    ChangeRecord,
    ExpectationStatus,
    ExpectedVsActual,
    StateTransition,
    TemporalEvent,
    gen_temporal_id,
    utc_now,
)


class AttributionEngine:
    """Attributes changes to actions, events, or actors only when supported by evidence."""

    @classmethod
    def attribute_transition(
        cls,
        transition: StateTransition,
        candidate_causes: List[TemporalEvent],
    ) -> StateTransition:
        """Attempts to attribute a state transition to a candidate cause event."""
        if not candidate_causes:
            transition.attribution = AttributionCertainty.UNATTRIBUTED
            return transition

        # Find cause candidates that strictly preceded the transition timestamp
        valid_causes: List[Tuple[TemporalEvent, float]] = []

        for cause in candidate_causes:
            val_res = TemporalCausalityEngine.validate_temporal_precedence(
                cause_time=cause.clocks.event_time,
                effect_time=transition.timestamp,
                tolerance_seconds=0.0,
            )
            if not val_res.is_temporally_valid:
                # Contradiction: Candidate cause was timestamped AFTER the transition!
                continue

            valid_causes.append((cause, val_res.lag_seconds))

        if not valid_causes:
            transition.attribution = AttributionCertainty.UNATTRIBUTED
            return transition

        # Sort candidate causes by closest temporal proximity
        valid_causes.sort(key=lambda x: x[1])
        best_cause, lag_sec = valid_causes[0]

        # Check for explicit deterministic linkage (action ID, trigger ID, or correlation ID match)
        is_direct = (
            bool(transition.trigger_event_id) and (
                best_cause.canonical_event_id == transition.trigger_event_id
                or best_cause.causation_id == transition.trigger_event_id
            )
        ) or (
            bool(best_cause.correlation_id)
            and bool(transition.correlation_id)
            and best_cause.correlation_id == transition.correlation_id
        )

        same_entity = (
            bool(best_cause.source_entity_id)
            and best_cause.source_entity_id == transition.entity_id
        )

        if is_direct:
            transition.attribution = AttributionCertainty.DIRECTLY_ATTRIBUTED
            transition.attributed_cause = f"Event {best_cause.canonical_event_id} ({best_cause.event_type})"
            transition.actor = best_cause.actor_id or best_cause.source_subsystem
        elif same_entity and lag_sec < 5.0:
            transition.attribution = AttributionCertainty.STRONGLY_LINKED
            transition.attributed_cause = f"Event {best_cause.canonical_event_id} ({best_cause.event_type}) with {lag_sec:.2f}s lag"
        elif same_entity and lag_sec < 60.0:
            transition.attribution = AttributionCertainty.POSSIBLY_LINKED
            transition.attributed_cause = f"Event {best_cause.canonical_event_id} ({best_cause.event_type}) with {lag_sec:.2f}s lag"
        elif lag_sec < 60.0:
            transition.attribution = AttributionCertainty.CORRELATED
            transition.attributed_cause = f"Temporal correlation {lag_sec:.1f}s to {best_cause.canonical_event_id}"
        else:
            transition.attribution = AttributionCertainty.UNATTRIBUTED
            transition.attributed_cause = None

        return transition

    @classmethod
    def evaluate_expected_vs_actual(
        cls,
        subject_entity_id: str,
        expected_state: str,
        observed_state: str,
        expected_by: datetime,
        observed_at: datetime,
        expected_source: str = "action_postcondition",
        observed_source: str = "observation",
    ) -> ExpectedVsActual:
        """Evaluates whether an observed state matches the forecasted/expected state."""
        # Check if observed matches expected
        if expected_state.strip().lower() == observed_state.strip().lower():
            # Check timing
            if observed_at <= expected_by:
                status = ExpectationStatus.VERIFIED
                explanation = f"Observed state '{observed_state}' verified on schedule ({observed_at.isoformat()} <= {expected_by.isoformat()})."
            else:
                status = ExpectationStatus.VERIFIED
                lag = (observed_at - expected_by).total_seconds()
                explanation = f"Observed state '{observed_state}' verified with {lag:.1f}s delay."
        else:
            status = ExpectationStatus.CONTRADICTED
            explanation = f"Discrepancy: expected '{expected_state}' from {expected_source}, but observed '{observed_state}' from {observed_source}."

        return ExpectedVsActual(
            subject_entity_id=subject_entity_id,
            expected_state=expected_state,
            observed_state=observed_state,
            expected_by_time=expected_by,
            observed_time=observed_at,
            status=status,
            discrepancy_explanation=explanation,
            expected_source=expected_source,
            observed_source=observed_source,
            confidence=1.0 if status == ExpectationStatus.VERIFIED else 0.9,
        )
