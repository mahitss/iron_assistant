"""Deterministic 12-state capability lifecycle state machine (Task 91 Phase 2)."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone

from app.capability_lifecycle.models import (
    CapabilityMetadata,
    LifecycleState,
    LifecycleTransitionEvent,
    generate_cl_id,
    _now_utc,
)

logger = logging.getLogger("kairo.capability_lifecycle.state_machine")


class LifecycleTransitionError(Exception):
    """Raised when an illegal or unauthorized lifecycle state transition is attempted."""


class CapabilityStateMachine:
    """Enforces strict, deterministic lifecycle transitions with tamper-evident event logging."""

    # Authoritative allowed state transition graph
    TRANSITION_GRAPH: Dict[LifecycleState, Set[LifecycleState]] = {
        LifecycleState.DISCOVERED: {
            LifecycleState.VALIDATING,
            LifecycleState.BLOCKED,
            LifecycleState.FAILED,
        },
        LifecycleState.VALIDATING: {
            LifecycleState.VALIDATED,
            LifecycleState.FAILED,
            LifecycleState.BLOCKED,
        },
        LifecycleState.VALIDATED: {
            LifecycleState.SIMULATING,
            LifecycleState.CANARY,
            LifecycleState.ACTIVE,
            LifecycleState.BLOCKED,
            LifecycleState.FAILED,
        },
        LifecycleState.SIMULATING: {
            LifecycleState.VALIDATED,
            LifecycleState.CANARY,
            LifecycleState.ACTIVE,
            LifecycleState.BLOCKED,
            LifecycleState.FAILED,
        },
        LifecycleState.CANARY: {
            LifecycleState.ACTIVE,
            LifecycleState.DEGRADED,
            LifecycleState.VALIDATED,  # Canary aborted/rolled back cleanly
            LifecycleState.BLOCKED,
            LifecycleState.FAILED,
        },
        LifecycleState.ACTIVE: {
            LifecycleState.DEGRADED,
            LifecycleState.BLOCKED,
            LifecycleState.DEPRECATED,
            LifecycleState.FAILED,
        },
        LifecycleState.DEGRADED: {
            LifecycleState.ACTIVE,     # Recovered / stabilized
            LifecycleState.BLOCKED,
            LifecycleState.DEPRECATED,
            LifecycleState.FAILED,
        },
        LifecycleState.BLOCKED: {
            LifecycleState.VALIDATING, # Re-evaluation post-blocker resolution
            LifecycleState.ACTIVE,     # Unblocked by governance
            LifecycleState.DEPRECATED,
            LifecycleState.FAILED,
            LifecycleState.RETIRED,
        },
        LifecycleState.DEPRECATED: {
            LifecycleState.RETIRING,
            LifecycleState.BLOCKED,
            LifecycleState.FAILED,
        },
        LifecycleState.RETIRING: {
            LifecycleState.RETIRED,
            LifecycleState.BLOCKED,
            LifecycleState.FAILED,
        },
        LifecycleState.RETIRED: set(),  # Terminal state
        LifecycleState.FAILED: {
            LifecycleState.VALIDATING, # Retry validation
            LifecycleState.BLOCKED,
            LifecycleState.RETIRED,
        },
    }

    def __init__(self) -> None:
        self._event_log: List[LifecycleTransitionEvent] = []

    def can_transition(self, current_state: LifecycleState, target_state: LifecycleState) -> bool:
        """Determines whether a transition from current_state to target_state is legally permitted."""
        if current_state == target_state:
            return True  # Idempotent re-affirmation
        allowed = self.TRANSITION_GRAPH.get(current_state, set())
        return target_state in allowed

    def transition(
        self,
        capability: CapabilityMetadata,
        target_state: LifecycleState,
        reason: str,
        actor: str = "system",
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        safety_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[CapabilityMetadata, LifecycleTransitionEvent]:
        """Executes a transition, updates the capability, and emits an immutable transition event."""
        current = capability.lifecycle_state

        if current == target_state:
            logger.debug(
                "Idempotent transition request for capability %s: already in %s",
                capability.capability_id,
                target_state.value,
            )
            evt = LifecycleTransitionEvent(
                capability_id=capability.capability_id,
                version=capability.version,
                from_state=current,
                to_state=target_state,
                reason=f"Idempotent re-affirmation: {reason}",
                actor=actor,
                correlation_id=correlation_id or generate_cl_id("corr"),
                trace_id=trace_id,
                safety_metadata=safety_metadata or {},
            )
            self._event_log.append(evt)
            return capability, evt

        if not self.can_transition(current, target_state):
            err_msg = (
                f"Illegal lifecycle state transition attempted for capability '{capability.capability_id}' "
                f"from {current.value} to {target_state.value}. Allowed transitions: "
                f"{[s.value for s in self.TRANSITION_GRAPH.get(current, set())]}"
            )
            logger.error(err_msg)
            raise LifecycleTransitionError(err_msg)

        # Update capability state
        capability.lifecycle_state = target_state
        capability.updated_at = _now_utc()

        evt = LifecycleTransitionEvent(
            capability_id=capability.capability_id,
            version=capability.version,
            from_state=current,
            to_state=target_state,
            reason=reason,
            actor=actor,
            correlation_id=correlation_id or generate_cl_id("corr"),
            trace_id=trace_id,
            safety_metadata=safety_metadata or {},
        )
        self._event_log.append(evt)

        logger.info(
            "Lifecycle transition: %s [%s -> %s] by %s (reason: %s)",
            capability.capability_id,
            current.value,
            target_state.value,
            actor,
            reason,
        )
        return capability, evt

    def get_events_for_capability(self, capability_id: str) -> List[LifecycleTransitionEvent]:
        """Returns the chronological transition event history for a capability."""
        return [e for e in self._event_log if e.capability_id == capability_id]


_global_state_machine: Optional[CapabilityStateMachine] = None


def get_capability_state_machine() -> CapabilityStateMachine:
    global _global_state_machine
    if _global_state_machine is None:
        _global_state_machine = CapabilityStateMachine()
    return _global_state_machine
