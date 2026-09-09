"""Explicit state machine validators for Kairo domain entities (Task 39, Spec 38-40)."""

import logging

logger = logging.getLogger("kairo.state.machine")

# Explicit transition graphs
_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "task": {
        "PENDING": {"QUEUED", "RUNNING", "CANCELLED"},
        "QUEUED": {"RUNNING", "CANCELLED"},
        "RUNNING": {"COMPLETED", "FAILED", "CANCELLED", "RECOVERABLE", "PAUSED"},
        "PAUSED": {"RUNNING", "CANCELLED"},
        "RECOVERABLE": {"RUNNING", "FAILED", "CANCELLED"},
        "COMPLETED": {"ARCHIVED"},  # Terminal: cannot become RUNNING without explicit reopen
        "FAILED": {"QUEUED", "ARCHIVED"},  # Retry allowed via QUEUED
        "CANCELLED": {"ARCHIVED"},
        "ARCHIVED": set(),
    },
    "approval": {
        "PENDING": {"APPROVED", "REJECTED", "EXPIRED", "CANCELLED"},
        "APPROVED": set(),  # Terminal
        "REJECTED": set(),  # Terminal
        "EXPIRED": set(),  # Terminal
        "CANCELLED": set(),  # Terminal
    },
    "notification": {
        "QUEUED": {"SENT", "FAILED", "CANCELLED"},
        "SENT": {"READ", "DISMISSED", "ARCHIVED"},
        "READ": {"ARCHIVED"},
        "DISMISSED": {"ARCHIVED"},
        "FAILED": {"QUEUED", "ARCHIVED"},
        "CANCELLED": {"ARCHIVED"},
        "ARCHIVED": set(),
    },
    "device": {
        "DISCONNECTED": {"CONNECTED", "REVOKED"},
        "CONNECTED": {"DISCONNECTED", "REVOKED"},
        "REVOKED": set(),  # Terminal
    },
    "session": {
        "ACTIVE": {"EXPIRED", "REVOKED"},
        "EXPIRED": set(),  # Terminal
        "REVOKED": set(),  # Terminal
    },
    "incident": {
        "OPEN": {"ACKNOWLEDGED", "RESOLVED"},
        "ACKNOWLEDGED": {"RESOLVED"},
        "RESOLVED": set(),
    },
}


class StateMachineValidator:
    """Enforces valid state machine transitions across all entities."""

    @classmethod
    def is_valid_transition(cls, entity_type: str, current_state: str, new_state: str) -> bool:
        """Checks whether transitioning from current_state to new_state is permissible."""
        graph = _TRANSITIONS.get(entity_type.lower())
        if not graph:
            # If entity has no strict state machine defined, allow change if states differ
            return True

        current_norm = current_state.upper()
        new_norm = new_state.upper()

        if current_norm == new_norm:
            return True  # No-op transition is safe

        allowed_next = graph.get(current_norm, set())
        return new_norm in allowed_next

    @classmethod
    def validate_transition(cls, entity_type: str, current_state: str, new_state: str) -> None:
        """Validates state transition and raises ValueError if illegal."""
        if not cls.is_valid_transition(entity_type, current_state, new_state):
            msg = (
                f"Illegal state transition for '{entity_type}': "
                f"'{current_state.upper()}' cannot transition to '{new_state.upper()}'."
            )
            logger.warning(msg)
            raise ValueError(msg)
