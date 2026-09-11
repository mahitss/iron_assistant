"""Memory Lifecycle State Machine for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Enforces deterministic transitions across 14 memory lifecycle states (Spec 5).
Rejects illegal transitions (e.g. DELETED -> ACTIVE) and creates immutable audit records.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.memory_consolidation.schemas import (
    MemoryAuditEventType,
    MemoryLifecycleState,
)

logger = logging.getLogger("kairo.memory_consolidation.lifecycle")


class InvalidLifecycleTransitionError(Exception):
    """Raised when an illegal memory lifecycle state transition is requested."""

    pass


class MemoryLifecycleStateMachine:
    """State machine governing durable memory lifecycles (Spec 5)."""

    ALLOWED_TRANSITIONS: dict[MemoryLifecycleState, set[MemoryLifecycleState]] = {
        MemoryLifecycleState.CAPTURED: {
            MemoryLifecycleState.CLASSIFIED,
            MemoryLifecycleState.QUARANTINED,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.CLASSIFIED: {
            MemoryLifecycleState.VALIDATING,
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.QUARANTINED,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.VALIDATING: {
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.QUARANTINED,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.ACTIVE: {
            MemoryLifecycleState.CONSOLIDATING,
            MemoryLifecycleState.PROMOTED,
            MemoryLifecycleState.CONFLICTED,
            MemoryLifecycleState.QUARANTINED,
            MemoryLifecycleState.STALE,
            MemoryLifecycleState.SUPERSEDED,
            MemoryLifecycleState.EXPIRED,
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.CONSOLIDATING: {
            MemoryLifecycleState.CONSOLIDATED,
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.CONFLICTED,
            MemoryLifecycleState.QUARANTINED,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.CONSOLIDATED: {
            MemoryLifecycleState.PROMOTED,
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.STALE,
            MemoryLifecycleState.SUPERSEDED,
            MemoryLifecycleState.EXPIRED,
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.PROMOTED: {
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.STALE,
            MemoryLifecycleState.SUPERSEDED,
            MemoryLifecycleState.EXPIRED,
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.CONFLICTED: {
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.SUPERSEDED,
            MemoryLifecycleState.QUARANTINED,
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.QUARANTINED: {
            MemoryLifecycleState.VALIDATING,
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.STALE: {
            MemoryLifecycleState.ACTIVE,  # Re-validated with fresh evidence
            MemoryLifecycleState.SUPERSEDED,
            MemoryLifecycleState.EXPIRED,
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.SUPERSEDED: {
            MemoryLifecycleState.EXPIRED,
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.EXPIRED: {
            MemoryLifecycleState.FORGOTTEN,
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.FORGOTTEN: {
            MemoryLifecycleState.DELETED,
        },
        MemoryLifecycleState.DELETED: set(),  # Terminal state. Cannot silently revert.
    }

    @classmethod
    def can_transition(cls, current_state: MemoryLifecycleState, target_state: MemoryLifecycleState) -> bool:
        """Check if transition between lifecycle states is authorized."""
        if current_state == target_state:
            return True
        allowed = cls.ALLOWED_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    @classmethod
    def transition(
        cls,
        memory: Any,
        target_state: MemoryLifecycleState,
        actor: str = "system",
        reason: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute state transition with validation and audit generation (Spec 5, 33)."""
        current_state = (
            MemoryLifecycleState(memory.status) if isinstance(memory.status, str) else memory.status
        )

        if not cls.can_transition(current_state, target_state):
            err_msg = (
                f"INVALID_LIFECYCLE_TRANSITION: Cannot transition memory {memory.memory_id} "
                f"from {current_state.value} to {target_state.value}. State machine rejects invalid flow."
            )
            logger.warning(err_msg)
            raise InvalidLifecycleTransitionError(err_msg)

        previous_state_val = current_state.value
        memory.status = target_state
        if hasattr(memory, "version"):
            memory.version += 1

        audit_event = {
            "audit_id": f"maud_{uuid.uuid4().hex[:10]}",
            "memory_id": getattr(memory, "memory_id", "unknown"),
            "tenant_id": getattr(memory, "tenant_id", "default"),
            "event_type": cls._map_target_to_audit_event(target_state),
            "actor": actor,
            "previous_state": previous_state_val,
            "new_state": target_state.value,
            "reason": reason,
            "details": details or {},
            "timestamp": datetime.now(UTC),
        }
        return audit_event

    @staticmethod
    def _map_target_to_audit_event(target: MemoryLifecycleState) -> str:
        mapping = {
            MemoryLifecycleState.CAPTURED: MemoryAuditEventType.MEMORY_CAPTURED.value,
            MemoryLifecycleState.CLASSIFIED: MemoryAuditEventType.MEMORY_CLASSIFIED.value,
            MemoryLifecycleState.VALIDATING: MemoryAuditEventType.MEMORY_VALIDATED.value,
            MemoryLifecycleState.ACTIVE: "MEMORY_ACTIVATED",
            MemoryLifecycleState.CONSOLIDATING: "MEMORY_CONSOLIDATION_STARTED",
            MemoryLifecycleState.CONSOLIDATED: MemoryAuditEventType.MEMORY_CONSOLIDATED.value,
            MemoryLifecycleState.PROMOTED: MemoryAuditEventType.MEMORY_PROMOTED.value,
            MemoryLifecycleState.CONFLICTED: MemoryAuditEventType.MEMORY_CONFLICT_DETECTED.value,
            MemoryLifecycleState.QUARANTINED: MemoryAuditEventType.MEMORY_QUARANTINED.value,
            MemoryLifecycleState.STALE: "MEMORY_STALE_FLAGGED",
            MemoryLifecycleState.SUPERSEDED: MemoryAuditEventType.MEMORY_SUPERSEDED.value,
            MemoryLifecycleState.EXPIRED: MemoryAuditEventType.MEMORY_EXPIRED.value,
            MemoryLifecycleState.FORGOTTEN: MemoryAuditEventType.MEMORY_FORGOTTEN.value,
            MemoryLifecycleState.DELETED: MemoryAuditEventType.MEMORY_DELETED.value,
        }
        return mapping.get(target, "MEMORY_STATE_CHANGED")
