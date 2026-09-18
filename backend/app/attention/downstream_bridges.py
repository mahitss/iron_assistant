"""Downstream Subsystem Integration Bridges (Task 109, Spec 13-25, 41, 48, 49).

Preserves Core Invariants:
1. ATTENTION != DECISION (Task 94 Decision Intelligence is sole decider).
2. ATTENTION != RESOURCE ALLOCATION AUTHORITY (Task 77 Resource Economy allocates).
3. ATTENTION != GOAL (Task 100 Mission Control manages goals).
4. ATTENTION != ACTION (Zero action execution primitives).
5. ATTENTION != AUTHORIZATION (SecurityCenter authorizes).
6. EMERGENCY_STOP ABSOLUTE PRIMACY (Immediately surfaced, fail-closed).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import UTC, datetime

from app.attention.domain import (
    AttentionAllocation,
    AttentionCandidate,
    AttentionDecision,
    AttentionFeedback,
    AttentionScore,
    AttentionSnapshot,
    FocusSession,
    FocusTarget,
    InterruptionClassification,
    gen_attn_id,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class SubsystemBridges:
    """Non-authoritative integration bridges between Attention and Kairo subsystems."""

    @classmethod
    def create_resource_economy_request(
        cls,
        candidate: AttentionCandidate,
        resource_class: str = "STANDARD_REASONING",
    ) -> AttentionAllocation:
        """Formats and submits a formal demand request to Task 77 Resource Economy (Spec 24)."""
        # Estimates reasoning cost based on uncertainty and complexity
        estimated_cost = round(1.0 + (candidate.uncertainty * 2.0), 2)
        expected_benefit = candidate.score.composite_salience

        return AttentionAllocation(
            allocation_id=gen_attn_id("aalloc"),
            candidate_id=candidate.candidate_id,
            estimated_reasoning_cost=estimated_cost,
            expected_benefit=expected_benefit,
            urgency=candidate.score.urgency,
            resource_class=resource_class,
            deadline=candidate.deadline,
            economy_status="REQUESTED",
            created_at=utc_now(),
        )

    @classmethod
    def emit_decision_recommendation(
        cls,
        candidate: AttentionCandidate,
        classification: InterruptionClassification,
        target: Optional[FocusTarget] = None,
    ) -> AttentionDecision:
        """Surfaces non-authoritative routing recommendation to Task 94 Decision Engine (Spec 48)."""
        rationale = (
            f"Attention engine recommends {classification.value} based on composite salience "
            f"{candidate.score.composite_salience:.2f} (urgency={candidate.score.urgency:.2f}, "
            f"risk={candidate.score.risk:.2f})."
        )
        return AttentionDecision(
            recommendation_id=gen_attn_id("arec"),
            candidate_id=candidate.candidate_id,
            recommended_routing=classification,
            suggested_focus_target=target,
            salience=candidate.score,
            rationale=rationale,
            created_at=utc_now(),
        )

    @classmethod
    def create_decision_snapshot(
        cls,
        active_session: Optional[FocusSession],
        nested_stack: List[FocusSession],
        queue: List[AttentionCandidate],
        health_status: Any,
        active_missions: Optional[List[str]] = None,
        active_intents: Optional[List[str]] = None,
    ) -> AttentionSnapshot:
        """Captures immutable point-in-time state for Task 94 Decision Engine (Spec 41)."""
        queue_summary = [
            {
                "candidate_id": c.candidate_id,
                "title": c.title,
                "type": c.type.value if hasattr(c.type, "value") else str(c.type),
                "composite_salience": c.score.composite_salience,
                "urgency": c.score.urgency,
                "lifecycle": c.lifecycle.value if hasattr(c.lifecycle, "value") else str(c.lifecycle),
            }
            for c in queue[:15]
        ]
        return AttentionSnapshot(
            snapshot_id=gen_attn_id("asnap"),
            created_at=utc_now(),
            active_focus_session=active_session,
            nested_stack_sessions=nested_stack,
            queue_summary=queue_summary,
            health_status=health_status,
            active_missions=active_missions or [],
            active_intents=active_intents or [],
        )

    @classmethod
    def record_feedback(
        cls,
        candidate_id: str,
        decision_type: str,
        was_appropriate: bool,
        missed_critical: bool = False,
        unnecessary_interrupt: bool = False,
        starvation_occurred: bool = False,
        notes: str = "",
    ) -> AttentionFeedback:
        """Records post-hoc evaluation telemetry for Task 104 Evaluation Engine (Spec 43)."""
        return AttentionFeedback(
            feedback_id=gen_attn_id("afbk"),
            candidate_id=candidate_id,
            decision_type=decision_type,
            was_appropriate=was_appropriate,
            missed_critical=missed_critical,
            unnecessary_interrupt=unnecessary_interrupt,
            starvation_occurred=starvation_occurred,
            notes=notes,
            recorded_at=utc_now(),
        )
