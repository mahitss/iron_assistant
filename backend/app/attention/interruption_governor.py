"""Interruption Governance Engine and Switching Cost Calculator (Task 109, Spec 10, 11, 12).

Enforces:
- 6-tier interruption classification (NO_INTERRUPT, BACKGROUND, DEFER, WATCH, INTERRUPT, IMMEDIATE_INTERRUPT)
- Multi-dimensional switching cost calculation
- EmergencyStop absolute primacy (fail-closed, immediate preemption)
- Non-interruptible critical commit phase shielding
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.attention.domain import (
    AttentionCandidate,
    FocusSession,
    InterruptionClassification,
    InterruptionCostBreakdown,
    InterruptionDecision,
    InterruptionRequest,
)


class InterruptionGovernor:
    """Evaluates inbound interruption requests against active focus and switching costs."""

    @classmethod
    def calculate_switching_cost(
        cls,
        current_session: Optional[FocusSession],
        current_phase: str = "in_progress",  # early, in_progress, critical_commit, finalizing
        current_progress_pct: float = 50.0,
        is_recomputation_expensive: bool = False,
    ) -> InterruptionCostBreakdown:
        """Calculates multi-dimensional switching cost if current focus is interrupted."""
        if current_session is None:
            return InterruptionCostBreakdown(
                lost_context_cost=0.0,
                lost_progress_cost=0.0,
                recomputation_cost=0.0,
                resource_cost=0.0,
                deadline_risk=0.0,
                cognitive_fragmentation_risk=0.0,
                action_safety_risk=0.0,
                total_interruption_cost=0.0,
            )

        # 1. Lost context cost: higher for deep nested sessions
        depth = current_session.depth
        lost_context = min(0.9, 0.2 + (depth * 0.15))

        # 2. Lost progress cost
        lost_progress = (current_progress_pct / 100.0) * 0.5

        # 3. Recomputation cost
        recomputation = 0.6 if is_recomputation_expensive else 0.2

        # 4. Phase-specific risks
        if current_phase == "critical_commit":
            safety_risk = 0.95
            total = 0.90
        elif current_phase == "finalizing":
            safety_risk = 0.4
            total = 0.60
        else:
            safety_risk = 0.1
            total = min(0.85, (lost_context * 0.35 + lost_progress * 0.25 + recomputation * 0.25 + 0.15))

        return InterruptionCostBreakdown(
            lost_context_cost=round(lost_context, 3),
            lost_progress_cost=round(lost_progress, 3),
            recomputation_cost=round(recomputation, 3),
            resource_cost=0.2,
            deadline_risk=0.1,
            cognitive_fragmentation_risk=0.25 if depth >= 3 else 0.1,
            action_safety_risk=round(safety_risk, 3),
            total_interruption_cost=round(total, 3),
        )

    @classmethod
    def evaluate(
        cls,
        request: InterruptionRequest,
        incoming: AttentionCandidate,
        current_session: Optional[FocusSession],
        current_candidate: Optional[AttentionCandidate],
        current_phase: str = "in_progress",
        is_current_non_interruptible: bool = False,
    ) -> InterruptionDecision:
        """Evaluates whether and how incoming candidate should interrupt current focus."""
        # 1. EmergencyStop Absolute Primacy (Spec 10, 40)
        if request.source_is_emergency_stop or incoming.type == "SAFETY" and "EMERGENCY" in incoming.title.upper():
            return InterruptionDecision(
                request_id=request.request_id,
                incoming_candidate_id=incoming.candidate_id,
                classification=InterruptionClassification.IMMEDIATE_INTERRUPT,
                should_interrupt=True,
                cost_breakdown=cls.calculate_switching_cost(current_session, current_phase),
                reason="EMERGENCY_STOP ABSOLUTE PRIMACY: Immediate preemption required fail-closed.",
            )

        # 2. If no active focus exists, immediate focus is granted
        if current_session is None or current_candidate is None:
            return InterruptionDecision(
                request_id=request.request_id,
                incoming_candidate_id=incoming.candidate_id,
                classification=InterruptionClassification.INTERRUPT,
                should_interrupt=True,
                cost_breakdown=InterruptionCostBreakdown(total_interruption_cost=0.0),
                reason="No active focus session; incoming candidate allocated active focus.",
            )

        # 3. Shielded or Non-interruptible Critical Commit Phase Protection
        cost_breakdown = cls.calculate_switching_cost(current_session, current_phase)
        is_shielded = (
            is_current_non_interruptible
            or current_phase == "critical_commit"
            or current_session.interruption_policy == "SHIELDED"
        )

        if is_shielded and incoming.score.urgency < 0.95 and incoming.score.risk < 0.9:
            # Shielded work defers or backgrounds incoming stimulus
            if incoming.score.composite_salience >= 0.6:
                return InterruptionDecision(
                    request_id=request.request_id,
                    incoming_candidate_id=incoming.candidate_id,
                    classification=InterruptionClassification.DEFER,
                    should_interrupt=False,
                    cost_breakdown=cost_breakdown,
                    reason=f"Current focus is in shielded {current_phase} phase; incoming deferred.",
                )
            else:
                return InterruptionDecision(
                    request_id=request.request_id,
                    incoming_candidate_id=incoming.candidate_id,
                    classification=InterruptionClassification.NO_INTERRUPT,
                    should_interrupt=False,
                    cost_breakdown=cost_breakdown,
                    reason=f"Current focus is in shielded {current_phase} phase; incoming rejected.",
                )

        # 4. Salience & Urgency Comparison
        incoming_salience = incoming.score.composite_salience
        current_salience = current_candidate.score.composite_salience
        salience_delta = incoming_salience - current_salience
        switching_penalty = cost_breakdown.total_interruption_cost

        # Critical Security / Incident override
        if incoming.score.risk >= 0.85 and incoming.score.urgency >= 0.85:
            return InterruptionDecision(
                request_id=request.request_id,
                incoming_candidate_id=incoming.candidate_id,
                classification=InterruptionClassification.IMMEDIATE_INTERRUPT,
                should_interrupt=True,
                cost_breakdown=cost_breakdown,
                reason=f"Critical high-risk incident '{incoming.title}' overrides active focus.",
            )

        # Standard interrupt threshold: incoming salience must exceed current + switching cost
        if salience_delta > (0.25 + (switching_penalty * 0.3)) and incoming.score.urgency >= 0.7:
            return InterruptionDecision(
                request_id=request.request_id,
                incoming_candidate_id=incoming.candidate_id,
                classification=InterruptionClassification.INTERRUPT,
                should_interrupt=True,
                cost_breakdown=cost_breakdown,
                reason=(
                    f"Approved: Salience delta ({salience_delta:.2f}) justifies switching cost "
                    f"({switching_penalty:.2f})."
                ),
            )

        # Can incoming run in background?
        if incoming.type in ("BACKGROUND", "LEARNING", "VERIFICATION", "MAINTENANCE") or incoming.score.resource_cost < 0.3:
            return InterruptionDecision(
                request_id=request.request_id,
                incoming_candidate_id=incoming.candidate_id,
                classification=InterruptionClassification.BACKGROUND,
                should_interrupt=False,
                cost_breakdown=cost_breakdown,
                reason="Incoming candidate suitable for concurrent background evaluation.",
            )

        # Is incoming waiting on an external condition?
        if "WAITING" in incoming.metadata or "watch_condition" in incoming.metadata:
            return InterruptionDecision(
                request_id=request.request_id,
                incoming_candidate_id=incoming.candidate_id,
                classification=InterruptionClassification.WATCH,
                should_interrupt=False,
                cost_breakdown=cost_breakdown,
                reason="Incoming candidate placed on bounded watch until condition satisfied.",
            )

        # Otherwise, defer or reject
        if incoming_salience >= 0.4:
            return InterruptionDecision(
                request_id=request.request_id,
                incoming_candidate_id=incoming.candidate_id,
                classification=InterruptionClassification.DEFER,
                should_interrupt=False,
                cost_breakdown=cost_breakdown,
                reason="Insufficient salience delta to preempt active focus; deferred to queue.",
            )

        return InterruptionDecision(
            request_id=request.request_id,
            incoming_candidate_id=incoming.candidate_id,
            classification=InterruptionClassification.NO_INTERRUPT,
            should_interrupt=False,
            cost_breakdown=cost_breakdown,
            reason="Incoming candidate lacks sufficient salience to interrupt or defer.",
        )
