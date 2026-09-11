"""Attention Lifecycle State Machine (Task 70).

Enforces explicit 12-state transitions and prevents invalid state mutations:
UNSEEN -> OBSERVED -> QUEUED -> ATTENDING -> RESOLVED
With explicit branches for MONITORING, DEFERRED, DELEGATED, PAUSED, BLOCKED, DISMISSED, EXPIRED.
"""

from app.attention.schemas import AttentionState


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal attention state transition is attempted."""

    pass


class AttentionLifecycleStateMachine:
    """Validates and applies attention candidate state transitions."""

    # Explicit allowed state transitions
    VALID_TRANSITIONS: dict[AttentionState, set[AttentionState]] = {
        AttentionState.UNSEEN: {
            AttentionState.OBSERVED,
            AttentionState.DISMISSED,
        },
        AttentionState.OBSERVED: {
            AttentionState.QUEUED,
            AttentionState.ATTENDING,
            AttentionState.MONITORING,
            AttentionState.DEFERRED,
            AttentionState.DISMISSED,
        },
        AttentionState.QUEUED: {
            AttentionState.ATTENDING,
            AttentionState.MONITORING,
            AttentionState.DEFERRED,
            AttentionState.DELEGATED,
            AttentionState.DISMISSED,
            AttentionState.EXPIRED,
            AttentionState.BLOCKED,
        },
        AttentionState.ATTENDING: {
            AttentionState.PAUSED,
            AttentionState.MONITORING,
            AttentionState.DEFERRED,
            AttentionState.DELEGATED,
            AttentionState.RESOLVED,
            AttentionState.BLOCKED,
            AttentionState.DISMISSED,
        },
        AttentionState.MONITORING: {
            AttentionState.QUEUED,
            AttentionState.ATTENDING,
            AttentionState.RESOLVED,
            AttentionState.DISMISSED,
            AttentionState.EXPIRED,
            AttentionState.DEFERRED,
        },
        AttentionState.DEFERRED: {
            AttentionState.QUEUED,
            AttentionState.ATTENDING,
            AttentionState.DELEGATED,
            AttentionState.DISMISSED,
            AttentionState.EXPIRED,
        },
        AttentionState.DELEGATED: {
            AttentionState.ATTENDING,  # Reclaimed / handoff
            AttentionState.RESOLVED,
            AttentionState.DISMISSED,
            AttentionState.BLOCKED,
        },
        AttentionState.PAUSED: {
            AttentionState.ATTENDING,  # Resumed
            AttentionState.QUEUED,
            AttentionState.DEFERRED,
            AttentionState.DISMISSED,
            AttentionState.RESOLVED,
        },
        AttentionState.RESOLVED: {
            # Terminal states can only transition to OBSERVED if a legitimate new signal is observed
            AttentionState.OBSERVED,
        },
        AttentionState.DISMISSED: {
            AttentionState.OBSERVED,
        },
        AttentionState.EXPIRED: {
            AttentionState.OBSERVED,
        },
        AttentionState.BLOCKED: {
            AttentionState.QUEUED,
            AttentionState.ATTENDING,
            AttentionState.DEFERRED,
            AttentionState.DISMISSED,
        },
    }

    TERMINAL_STATES = {AttentionState.RESOLVED, AttentionState.DISMISSED, AttentionState.EXPIRED}

    @classmethod
    def can_transition(
        cls,
        from_state: AttentionState,
        to_state: AttentionState,
        *,
        has_new_signal: bool = False,
    ) -> tuple[bool, str]:
        """Check if transition from `from_state` to `to_state` is legal."""
        if from_state == to_state:
            return True, "No-op transition"

        # Check if from_state is terminal
        if from_state in cls.TERMINAL_STATES:
            if not has_new_signal:
                return (
                    False,
                    f"Cannot transition from terminal state {from_state.value} to {to_state.value} without a new signal/event.",
                )
            if to_state != AttentionState.OBSERVED:
                return (
                    False,
                    f"Reopening from terminal state {from_state.value} must transition to OBSERVED first, not {to_state.value}.",
                )

        allowed = cls.VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            return (
                False,
                f"Invalid attention transition: {from_state.value} -> {to_state.value}. Allowed targets: {[s.value for s in allowed]}",
            )

        return True, f"Valid transition from {from_state.value} to {to_state.value}"

    @classmethod
    def transition(
        cls,
        from_state: AttentionState,
        to_state: AttentionState,
        *,
        has_new_signal: bool = False,
    ) -> AttentionState:
        """Validate and apply transition, raising InvalidStateTransitionError if illegal."""
        valid, reason = cls.can_transition(from_state, to_state, has_new_signal=has_new_signal)
        if not valid:
            raise InvalidStateTransitionError(reason)
        return to_state
