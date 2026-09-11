"""Reasoning Lifecycle State Machine (Task 71).

Enforces explicit 15-state transitions and prevents invalid epistemic leaps:
CREATED -> UNDERSTANDING -> DECOMPOSING -> HYPOTHESIS_GENERATION -> EVIDENCE_COLLECTION
  -> EVIDENCE_EVALUATION -> DELIBERATING -> CONCLUDING -> VERIFYING -> COMPLETED
With explicit branches for BLOCKED, UNCERTAIN, FAILED, ABORTED, NEEDS_INFORMATION.
"""

from typing import Any

from app.reasoning.schemas import ReasoningState


class InvalidReasoningStateTransitionError(ValueError):
    """Raised when an illegal reasoning state transition is attempted."""

    pass


IllegalStateTransitionError = InvalidReasoningStateTransitionError


class ReasoningStateMachine:
    """Validates and enforces deterministic transitions across the 15 reasoning states."""

    VALID_TRANSITIONS: dict[ReasoningState, set[ReasoningState]] = {
        ReasoningState.CREATED: {
            ReasoningState.UNDERSTANDING,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.UNDERSTANDING: {
            ReasoningState.DECOMPOSING,
            ReasoningState.HYPOTHESIS_GENERATION,  # Direct quick path
            ReasoningState.NEEDS_INFORMATION,
            ReasoningState.BLOCKED,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.DECOMPOSING: {
            ReasoningState.HYPOTHESIS_GENERATION,
            ReasoningState.NEEDS_INFORMATION,
            ReasoningState.BLOCKED,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.HYPOTHESIS_GENERATION: {
            ReasoningState.EVIDENCE_COLLECTION,
            ReasoningState.NEEDS_INFORMATION,
            ReasoningState.BLOCKED,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.EVIDENCE_COLLECTION: {
            ReasoningState.EVIDENCE_EVALUATION,
            ReasoningState.NEEDS_INFORMATION,
            ReasoningState.BLOCKED,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.EVIDENCE_EVALUATION: {
            ReasoningState.DELIBERATING,
            ReasoningState.EVIDENCE_COLLECTION,  # More evidence needed
            ReasoningState.UNCERTAIN,
            ReasoningState.BLOCKED,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.DELIBERATING: {
            ReasoningState.CONCLUDING,
            ReasoningState.EVIDENCE_COLLECTION,  # Counterarguments demand more evidence
            ReasoningState.HYPOTHESIS_GENERATION,  # New hypothesis emerged
            ReasoningState.UNCERTAIN,
            ReasoningState.BLOCKED,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.CONCLUDING: {
            ReasoningState.VERIFYING,
            ReasoningState.COMPLETED,  # If verification not required for low-risk
            ReasoningState.UNCERTAIN,
            ReasoningState.BLOCKED,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.VERIFYING: {
            ReasoningState.COMPLETED,  # Verification passed
            ReasoningState.CONCLUDING,  # Adjusting conclusion based on verification
            ReasoningState.EVIDENCE_COLLECTION,  # Verification failed; collect more evidence
            ReasoningState.UNCERTAIN,
            ReasoningState.FAILED,
            ReasoningState.ABORTED,
        },
        ReasoningState.COMPLETED: {
            # Terminal state; reassessment can reopen back to EVIDENCE_COLLECTION or DELIBERATING
            ReasoningState.EVIDENCE_COLLECTION,
            ReasoningState.DELIBERATING,
        },
        ReasoningState.BLOCKED: {
            ReasoningState.UNDERSTANDING,
            ReasoningState.EVIDENCE_COLLECTION,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.UNCERTAIN: {
            # Cannot leap directly to VERIFIED or COMPLETED! Must gather evidence or deliberate
            ReasoningState.EVIDENCE_COLLECTION,
            ReasoningState.DELIBERATING,
            ReasoningState.NEEDS_INFORMATION,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.NEEDS_INFORMATION: {
            ReasoningState.UNDERSTANDING,
            ReasoningState.EVIDENCE_COLLECTION,
            ReasoningState.DELIBERATING,
            ReasoningState.ABORTED,
            ReasoningState.FAILED,
        },
        ReasoningState.FAILED: {
            ReasoningState.CREATED,  # Retry
        },
        ReasoningState.ABORTED: {
            ReasoningState.CREATED,  # Re-initiate
        },
    }

    TERMINAL_STATES = {
        ReasoningState.COMPLETED,
        ReasoningState.FAILED,
        ReasoningState.ABORTED,
    }

    @classmethod
    def can_transition(cls, from_state: Any, to_state: Any) -> bool:
        """Check whether a transition between two states is valid."""
        valid, _ = cls.validate_transition(from_state, to_state)
        return valid

    @classmethod
    def validate_transition(cls, from_state: Any, to_state: Any) -> tuple[bool, str]:
        """Validate whether a transition between two states is valid and provide reason."""
        if hasattr(from_state, "current_state"):
            from_state = from_state.current_state
        if hasattr(to_state, "current_state"):
            to_state = to_state.current_state

        from_state = ReasoningState(from_state)
        to_state = ReasoningState(to_state)

        if from_state == to_state:
            return True, "No-op transition"

        allowed = cls.VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            return (
                False,
                f"Invalid reasoning state transition: {from_state.value} -> {to_state.value}. Allowed: {[s.value for s in allowed]}",
            )

        return True, f"Valid transition from {from_state.value} to {to_state.value}"

    @classmethod
    def transition(cls, target: Any, to_state: Any) -> ReasoningState:
        """Validate and apply transition, raising InvalidReasoningStateTransitionError if illegal."""
        if hasattr(target, "current_state"):
            from_state = target.current_state
            valid, reason = cls.validate_transition(from_state, to_state)
            if not valid:
                raise InvalidReasoningStateTransitionError(reason)
            target.current_state = ReasoningState(to_state)
            return target.current_state
        else:
            valid, reason = cls.validate_transition(target, to_state)
            if not valid:
                raise InvalidReasoningStateTransitionError(reason)
            return ReasoningState(to_state)

    @classmethod
    def is_terminal(cls, state: Any) -> bool:
        """Check whether a state is terminal."""
        if hasattr(state, "current_state"):
            state = state.current_state
        return ReasoningState(state) in cls.TERMINAL_STATES
