"""Interruption and Preemption Policy Engine (Task 70).

Determines when an incoming attention candidate B should interrupt ongoing work A:
- Critical production outages interrupt normal work.
- Low-priority research findings do not interrupt active tasks.
- Respects FOCUS_MODE, NORMAL_MODE, EMERGENCY_MODE.
- Protects critical commit points and non-interruptible execution phases.
- Guarantees state preservation before preemption.
"""

from app.attention.schemas import AttentionCandidate, AttentionMode, PreemptionDecision


class InterruptionPolicyEngine:
    """Evaluates whether to preempt current focus and orchestrates state preservation."""

    # Interruption score delta threshold required in NORMAL_MODE
    NORMAL_PREEMPTION_DELTA = 0.25

    # Interruption score delta threshold required in FOCUS_MODE
    FOCUS_PREEMPTION_DELTA = 0.45

    @classmethod
    def evaluate_interruption(
        cls,
        *,
        incoming: AttentionCandidate,
        current: AttentionCandidate | None,
        mode: AttentionMode = AttentionMode.NORMAL_MODE,
        current_phase: str = "in_progress",  # "early", "in_progress", "critical_commit", "finalizing"
        is_current_non_interruptible: bool = False,
    ) -> PreemptionDecision:
        """Evaluate whether incoming candidate should interrupt current focus."""
        if current is None:
            return PreemptionDecision(
                should_interrupt=True,
                incoming_id=incoming.attention_id,
                current_id=None,
                incoming_score=incoming.attention_score,
                current_score=0.0,
                urgency_delta=incoming.urgency,
                interrupt_cost=0.0,
                reason="No active focus; immediate allocation granted.",
                state_preserved=False,
            )

        # 1. Non-interruptible critical phase protection (unless incoming is critical emergency)
        if is_current_non_interruptible or current_phase == "critical_commit":
            if incoming.severity != "CRITICAL" and incoming.urgency < 0.95:
                return PreemptionDecision(
                    should_interrupt=False,
                    incoming_id=incoming.attention_id,
                    current_id=current.attention_id,
                    incoming_score=incoming.attention_score,
                    current_score=current.attention_score,
                    urgency_delta=incoming.urgency - current.urgency,
                    interrupt_cost=0.9,
                    reason=f"Current focus '{current.title}' is in non-interruptible critical commit phase.",
                    state_preserved=False,
                )

        # 2. Critical Safety & Production Outage Invariant:
        # Critical incidents with high urgency ALWAYS interrupt lower priority tasks
        is_incoming_critical = incoming.severity == "CRITICAL" or incoming.urgency >= 0.85
        is_current_critical = current.severity == "CRITICAL" or current.urgency >= 0.85

        if is_incoming_critical and not is_current_critical:
            return PreemptionDecision(
                should_interrupt=True,
                incoming_id=incoming.attention_id,
                current_id=current.attention_id,
                incoming_score=incoming.attention_score,
                current_score=current.attention_score,
                urgency_delta=round(incoming.urgency - current.urgency, 3),
                interrupt_cost=0.2,
                reason=f"Critical safety/incident preemption: '{incoming.title}' preempts '{current.title}'.",
                state_preserved=False,  # to be marked True once snapshot created
            )

        # 3. Calculate score delta and switching cost
        score_delta = incoming.attention_score - current.attention_score
        urgency_delta = incoming.urgency - current.urgency

        # Switching cost calculation
        phase_cost_map = {
            "early": 0.1,
            "in_progress": 0.2,
            "finalizing": 0.35,
            "critical_commit": 0.8,
        }
        interrupt_cost = phase_cost_map.get(current_phase, 0.2)

        # 4. Mode-specific threshold checking
        if mode == AttentionMode.FOCUS_MODE:
            # Focus mode dampens interruptions: incoming must substantially exceed current
            threshold_needed = cls.FOCUS_PREEMPTION_DELTA + interrupt_cost
            if score_delta >= threshold_needed and incoming.urgency >= 0.75:
                should_interrupt = True
                reason = (
                    f"FOCUS_MODE interrupt approved: incoming score delta ({score_delta:.2f}) "
                    f"exceeds threshold ({threshold_needed:.2f})."
                )
            else:
                should_interrupt = False
                reason = (
                    f"FOCUS_MODE active: incoming score delta ({score_delta:.2f}) "
                    f"insufficient to interrupt active focus '{current.title}' (required {threshold_needed:.2f})."
                )

        elif mode == AttentionMode.EMERGENCY_MODE:
            # Emergency mode allows high-urgency items to take focus rapidly
            should_interrupt = incoming.urgency >= 0.65 or score_delta > 0.1
            reason = (
                f"EMERGENCY_MODE active: preemption {'approved' if should_interrupt else 'denied'} "
                f"for '{incoming.title}'."
            )

        else:  # NORMAL_MODE
            threshold_needed = cls.NORMAL_PREEMPTION_DELTA + interrupt_cost
            if score_delta >= threshold_needed or (urgency_delta > 0.4 and incoming.urgency > 0.7):
                should_interrupt = True
                reason = (
                    f"Normal preemption approved: incoming score {incoming.attention_score:.2f} "
                    f"exceeds current {current.attention_score:.2f} by required margin ({score_delta:.2f} >= {threshold_needed:.2f})."
                )
            else:
                should_interrupt = False
                reason = (
                    f"Normal preemption denied: incoming score delta ({score_delta:.2f}) "
                    f"does not overcome interruption cost ({interrupt_cost:.2f})."
                )

        return PreemptionDecision(
            should_interrupt=should_interrupt,
            incoming_id=incoming.attention_id,
            current_id=current.attention_id,
            incoming_score=incoming.attention_score,
            current_score=current.attention_score,
            urgency_delta=round(urgency_delta, 3),
            interrupt_cost=round(interrupt_cost, 3),
            reason=reason,
            state_preserved=False,
        )
