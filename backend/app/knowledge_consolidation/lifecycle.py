"""Deterministic lifecycle and state transition engine for KAIRO knowledge (Task 92 Phase 2).

Guarantees:
- No arbitrary status mutation
- All transitions are recorded in an immutable audit trail
- Invalid transitions are strictly rejected
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.knowledge_consolidation.models import MemoryEntity, MemoryStatus

logger = logging.getLogger("kairo.knowledge_consolidation.lifecycle")


class InvalidStateTransitionError(Exception):
    """Raised when an illegal memory lifecycle state transition is attempted."""


# Explicit permitted transitions: source_status -> set of allowed destination statuses
PERMITTED_TRANSITIONS: dict[MemoryStatus, set[MemoryStatus]] = {
    MemoryStatus.CANDIDATE: {
        MemoryStatus.ACTIVE,
        MemoryStatus.ARCHIVED,
        MemoryStatus.BLOCKED,
        MemoryStatus.UNCERTAIN,
    },
    MemoryStatus.ACTIVE: {
        MemoryStatus.SUPERSEDED,
        MemoryStatus.CONFLICTED,
        MemoryStatus.STALE,
        MemoryStatus.INVALIDATED,
        MemoryStatus.ARCHIVED,
        MemoryStatus.BLOCKED,
        MemoryStatus.UNCERTAIN,
    },
    MemoryStatus.UNCERTAIN: {
        MemoryStatus.ACTIVE,
        MemoryStatus.CONFLICTED,
        MemoryStatus.INVALIDATED,
        MemoryStatus.ARCHIVED,
        MemoryStatus.BLOCKED,
    },
    MemoryStatus.CONFLICTED: {
        MemoryStatus.ACTIVE,
        MemoryStatus.INVALIDATED,
        MemoryStatus.SUPERSEDED,
        MemoryStatus.ARCHIVED,
        MemoryStatus.BLOCKED,
    },
    MemoryStatus.STALE: {
        MemoryStatus.ACTIVE,
        MemoryStatus.INVALIDATED,
        MemoryStatus.SUPERSEDED,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.INVALIDATED: {
        MemoryStatus.ARCHIVED,
        MemoryStatus.FORGOTTEN,
    },
    MemoryStatus.SUPERSEDED: {
        MemoryStatus.ARCHIVED,
        MemoryStatus.FORGOTTEN,
    },
    MemoryStatus.ARCHIVED: {
        MemoryStatus.FORGOTTEN,
        MemoryStatus.ACTIVE,  # Un-archive if needed
    },
    MemoryStatus.BLOCKED: {
        MemoryStatus.ACTIVE,
        MemoryStatus.INVALIDATED,
        MemoryStatus.ARCHIVED,
        MemoryStatus.FORGOTTEN,
    },
    MemoryStatus.FORGOTTEN: set(),  # Terminal state: cannot transition out
}


class MemoryLifecycleManager:
    """Enforces deterministic lifecycle transitions and audit logging."""

    def __init__(self) -> None:
        self._audit_trail: list[dict[str, Any]] = []

    def can_transition(self, current_status: MemoryStatus, target_status: MemoryStatus) -> bool:
        """Check if transition from current_status to target_status is permitted."""
        if current_status == target_status:
            return True
        allowed = PERMITTED_TRANSITIONS.get(current_status, set())
        return target_status in allowed

    def transition(
        self,
        memory: MemoryEntity,
        target_status: MemoryStatus,
        actor: str = "kairo_system",
        reason: str | None = None,
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> MemoryEntity:
        """Execute a validated state transition with immutable audit recording."""
        current_status = memory.status

        if current_status == target_status:
            return memory

        if not self.can_transition(current_status, target_status):
            err_msg = (
                f"Illegal memory lifecycle transition: '{current_status.value}' -> '{target_status.value}' "
                f"for memory '{memory.memory_id}'. Allowed: {[s.value for s in PERMITTED_TRANSITIONS.get(current_status, set())]}"
            )
            logger.warning(err_msg)
            raise InvalidStateTransitionError(err_msg)

        now = datetime.now(UTC)
        memory.status = target_status
        memory.updated_at = now

        # Record audit log entry
        audit_entry = {
            "timestamp": now.isoformat(),
            "memory_id": memory.memory_id,
            "previous_status": current_status.value,
            "new_status": target_status.value,
            "actor": actor,
            "reason": reason or f"Transition to {target_status.value}",
            "correlation_id": correlation_id,
            "details": details or {},
        }
        self._audit_trail.append(audit_entry)

        logger.info(
            "Memory '%s' transitioned: %s -> %s (actor=%s, reason=%s)",
            memory.memory_id,
            current_status.value,
            target_status.value,
            actor,
            reason,
        )
        return memory

    def get_history(self, memory_id: str) -> list[dict[str, Any]]:
        """Retrieve chronological lifecycle audit trail for a memory."""
        return [entry for entry in self._audit_trail if entry["memory_id"] == memory_id]
