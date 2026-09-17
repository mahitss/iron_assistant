"""State lifecycle validation and invariant rules engine for Task 98 (Phases 2 & 18).

Enforces:
- Deterministic, audited state transitions
- Contractual domain invariants
- Missing observation != healthy or unchanged state
- Execution != verified success
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.world_state.domain import (
    DriftSeverity,
    FreshnessState,
    StateInvariantViolation,
    StateStatus,
    WorldStateEntity,
    utc_now,
)

logger = logging.getLogger("kairo.world_state.lifecycle")


# =====================================================================
# VALID STATE TRANSITION MATRIX (Phase 2)
# =====================================================================

VALID_STATE_TRANSITIONS: dict[StateStatus, set[StateStatus]] = {
    StateStatus.UNKNOWN: {
        StateStatus.PROVISIONAL,
        StateStatus.OBSERVED,
        StateStatus.RECONSTRUCTING,
        StateStatus.INVALIDATED,
        StateStatus.ARCHIVED,
    },
    StateStatus.PROVISIONAL: {
        StateStatus.CURRENT,
        StateStatus.OBSERVED,
        StateStatus.UNCERTAIN,
        StateStatus.DEGRADED,
        StateStatus.INVALIDATED,
        StateStatus.ARCHIVED,
    },
    StateStatus.OBSERVED: {
        StateStatus.RECONSTRUCTING,
        StateStatus.CURRENT,
        StateStatus.UNCERTAIN,
        StateStatus.INVALIDATED,
    },
    StateStatus.RECONSTRUCTING: {
        StateStatus.CURRENT,
        StateStatus.CONFLICTED,
        StateStatus.DRIFTED,
        StateStatus.UNCERTAIN,
        StateStatus.INVALIDATED,
    },
    StateStatus.CURRENT: {
        StateStatus.DEGRADED,
        StateStatus.STALE,
        StateStatus.DRIFTED,
        StateStatus.CONFLICTED,
        StateStatus.UNCERTAIN,
        StateStatus.INVALIDATED,
        StateStatus.SUPERSEDED,
    },
    StateStatus.DEGRADED: {
        StateStatus.CURRENT,
        StateStatus.STALE,
        StateStatus.DRIFTED,
        StateStatus.CONFLICTED,
        StateStatus.ARCHIVED,
        StateStatus.SUPERSEDED,
    },
    StateStatus.STALE: {
        StateStatus.CURRENT,
        StateStatus.RECONSTRUCTING,
        StateStatus.DRIFTED,
        StateStatus.CONFLICTED,
        StateStatus.UNCERTAIN,
        StateStatus.INVALIDATED,
    },
    StateStatus.DRIFTED: {
        StateStatus.CURRENT,
        StateStatus.CONFLICTED,
        StateStatus.UNCERTAIN,
        StateStatus.INVALIDATED,
        StateStatus.SUPERSEDED,
    },
    StateStatus.CONFLICTED: {
        StateStatus.CURRENT,
        StateStatus.DRIFTED,
        StateStatus.UNCERTAIN,
        StateStatus.INVALIDATED,
        StateStatus.SUPERSEDED,
    },
    StateStatus.UNCERTAIN: {
        StateStatus.CURRENT,
        StateStatus.RECONSTRUCTING,
        StateStatus.CONFLICTED,
        StateStatus.DRIFTED,
        StateStatus.INVALIDATED,
    },
    StateStatus.INVALIDATED: {
        StateStatus.SUPERSEDED,
        StateStatus.ARCHIVED,
    },
    StateStatus.SUPERSEDED: {
        StateStatus.ARCHIVED,
    },
    StateStatus.ARCHIVED: set(),  # Terminal state
}


class StateLifecycleValidator:
    """Validates state transitions against the formal transition matrix."""

    @staticmethod
    def can_transition(current: StateStatus, target: StateStatus) -> bool:
        if current == target:
            return True
        allowed = VALID_STATE_TRANSITIONS.get(current, set())
        return target in allowed

    @staticmethod
    def validate_transition(current: StateStatus, target: StateStatus, entity_id: str) -> bool:
        if not StateLifecycleValidator.can_transition(current, target):
            logger.warning(
                "Illegal state transition rejected for entity %s: %s -> %s",
                entity_id,
                current.value,
                target.value,
            )
            return False
        return True


# =====================================================================
# STATE INVARIANT ENGINE (Phase 18)
# =====================================================================

class InvariantEngine:
    """Evaluates domain-level invariants across entities, capabilities, resources, and workflows."""

    def check_invariants(
        self,
        entity: WorldStateEntity,
        all_entities: Optional[dict[str, WorldStateEntity]] = None,
        now: Optional[datetime] = None,
    ) -> list[StateInvariantViolation]:
        """Instance method alias for evaluate_entity_invariants."""
        return self.evaluate_entity_invariants(entity, all_entities or {entity.entity_id: entity}, now=now)

    @staticmethod
    def evaluate_entity_invariants(
        entity: WorldStateEntity,
        all_entities: dict[str, WorldStateEntity],
        now: Optional[datetime] = None,
    ) -> list[StateInvariantViolation]:
        """Check formal invariants for a single state entity."""
        violations: list[StateInvariantViolation] = []
        current_time = now or utc_now()

        # Invariant 1: Freshness vs Status
        # If entity is stale past its update interval, it CANNOT masquerade as CURRENT healthy state
        if entity.is_stale(current_time) or entity.freshness == FreshnessState.STALE:
            if entity.status == StateStatus.CURRENT:
                violations.append(
                    StateInvariantViolation(
                        invariant_name="STALE_CANNOT_BE_CURRENT",
                        entity_id=entity.entity_id,
                        description=f"Entity '{entity.entity_id}' has elapsed its TTL or is STALE; cannot masquerade as CURRENT.",
                        severity=DriftSeverity.HIGH,
                        evidence={
                            "last_observed_at": entity.last_observed_at.isoformat(),
                            "expected_interval": entity.expected_update_interval_seconds,
                            "freshness": entity.freshness.value,
                            "status": entity.status.value,
                        },
                    )
                )

        # Invariant 2: Capability vs Capability Version
        # Active capability must reference a valid, non-retired capability version
        if entity.metadata.get("entity_type") == "CAPABILITY" or "capability" in entity.entity_id.lower():
            active_version = entity.metadata.get("active_version_id")
            if active_version:
                version_ent = all_entities.get(active_version)
                if version_ent:
                    is_retired = version_ent.metadata.get("is_retired", False) or version_ent.status == StateStatus.INVALIDATED
                    if is_retired and entity.status == StateStatus.CURRENT:
                        violations.append(
                            StateInvariantViolation(
                                invariant_name="ACTIVE_CAPABILITY_RETIRED_VERSION",
                                entity_id=entity.entity_id,
                                description=f"Capability '{entity.entity_id}' is active but bound to retired version '{active_version}'.",
                                severity=DriftSeverity.CRITICAL,
                                evidence={"active_version_id": active_version, "version_status": version_ent.status.value},
                            )
                        )

        # Invariant 3: Resource Consumption vs Allocated Quota
        # Observed resource utilization cannot exceed hard allocated budget
        allocated_quota = entity.metadata.get("allocated_quota")
        observed_usage = entity.attributes.get("resource_usage") or entity.attributes.get("cpu_percent")
        if allocated_quota is not None and observed_usage is not None:
            usage_val = observed_usage.current_value
            if isinstance(usage_val, (int, float)) and isinstance(allocated_quota, (int, float)):
                if usage_val > allocated_quota:
                    violations.append(
                        StateInvariantViolation(
                            invariant_name="RESOURCE_EXCEEDS_BUDGET",
                            entity_id=entity.entity_id,
                            description=f"Entity '{entity.entity_id}' observed consumption ({usage_val}) exceeds budget quota ({allocated_quota}).",
                            severity=DriftSeverity.HIGH,
                            evidence={"observed": usage_val, "allocated": allocated_quota},
                        )
                    )

        # Invariant 4: Postcondition Satisfaction on Completed Work
        # Completed task/workflow must have confirmed postconditions
        if entity.metadata.get("entity_type") in ("TASK", "WORKFLOW"):
            state_val = str(entity.metadata.get("state", "")).upper()
            if state_val == "COMPLETED":
                has_unmet_postcondition = entity.metadata.get("unmet_postconditions", False)
                if has_unmet_postcondition:
                    violations.append(
                        StateInvariantViolation(
                            invariant_name="COMPLETED_UNMET_POSTCONDITION",
                            entity_id=entity.entity_id,
                            description=f"Work '{entity.entity_id}' is marked COMPLETED but postconditions are unmet or unverified.",
                            severity=DriftSeverity.CRITICAL,
                            evidence={"state": state_val},
                        )
                    )

        return violations
