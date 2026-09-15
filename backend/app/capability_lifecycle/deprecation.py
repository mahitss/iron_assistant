"""Capability deprecation, sunset management, and auditable retirement (Task 91 Phase 12)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.capability_lifecycle.dependency_graph import CapabilityDependencyGraph, get_capability_dependency_graph
from app.capability_lifecycle.models import (
    CapabilityMetadata,
    DeprecationPlan,
    LifecycleState,
    generate_cl_id,
    _now_utc,
)
from app.capability_lifecycle.state_machine import CapabilityStateMachine, get_capability_state_machine

logger = logging.getLogger("kairo.capability_lifecycle.deprecation")


class CapabilityDeprecationManager:
    """Coordinates graceful deprecation, migration advisories, and dependency-safe retirement."""

    def __init__(
        self,
        state_machine: Optional[CapabilityStateMachine] = None,
        dependency_graph: Optional[CapabilityDependencyGraph] = None,
    ) -> None:
        self.state_machine = state_machine or get_capability_state_machine()
        self.dependency_graph = dependency_graph or get_capability_dependency_graph()
        # capability_id -> DeprecationPlan
        self._plans: Dict[str, DeprecationPlan] = {}

    def deprecate_capability(
        self,
        capability: CapabilityMetadata,
        reason: str,
        replacement_capability_id: Optional[str] = None,
        migration_guidance: str = "",
        sunset_days: int = 30,
        actor: str = "lifecycle_operator",
    ) -> DeprecationPlan:
        """Transitions capability to DEPRECATED state and establishes sunset timeline."""
        cap_id = capability.capability_id
        deadline = _now_utc() + timedelta(days=sunset_days)

        # Identify all currently dependent capabilities and consumers
        dependents = self.dependency_graph.get_dependents(cap_id)

        plan = DeprecationPlan(
            plan_id=generate_cl_id("depr"),
            capability_id=cap_id,
            version=capability.version,
            deprecation_reason=reason,
            replacement_capability_id=replacement_capability_id,
            migration_guidance=migration_guidance,
            affected_workflows=dependents,
            sunset_deadline=deadline,
            is_retired=False,
        )
        self._plans[cap_id] = plan

        capability.deprecation_reason = reason
        capability.replacement_capability_id = replacement_capability_id
        capability.sunset_deadline = deadline

        # State machine transition
        self.state_machine.transition(
            capability,
            LifecycleState.DEPRECATED,
            reason=f"Capability deprecated: {reason} (Sunset: {deadline.isoformat()})",
            actor=actor,
            safety_metadata={"plan_id": plan.plan_id, "affected_consumers": dependents},
        )

        logger.warning(
            "Capability '%s' marked DEPRECATED. Replacement: %s, Sunset: %s, Affected: %d",
            cap_id,
            replacement_capability_id or "None",
            deadline.isoformat(),
            len(dependents),
        )
        return plan

    def retire_capability(
        self,
        capability: CapabilityMetadata,
        force_retirement: bool = False,
        actor: str = "lifecycle_operator",
    ) -> Tuple[bool, str]:
        """Transitions capability from DEPRECATED -> RETIRING -> RETIRED, blocking if active consumers exist."""
        cap_id = capability.capability_id

        # 1. Check for Active Dependents
        dependents = self.dependency_graph.get_dependents(cap_id)
        if dependents and not force_retirement:
            err_msg = (
                f"Cannot retire capability '{cap_id}': Active dependent consumers exist: {dependents}. "
                "Consumers must be migrated or force_retirement=True required."
            )
            logger.warning(err_msg)
            return False, err_msg

        # 2. Transition DEPRECATED -> RETIRING
        if capability.lifecycle_state == LifecycleState.DEPRECATED:
            self.state_machine.transition(
                capability,
                LifecycleState.RETIRING,
                reason="Pre-retirement drain initiated",
                actor=actor,
            )

        # 3. Transition RETIRING -> RETIRED (Terminal)
        self.state_machine.transition(
            capability,
            LifecycleState.RETIRED,
            reason="Capability officially retired and deactivated permanently",
            actor=actor,
            safety_metadata={"force": force_retirement, "former_dependents": dependents},
        )

        # Clean up dependency graph
        self.dependency_graph.remove_capability(cap_id)

        plan = self._plans.get(cap_id)
        if plan:
            plan.is_retired = True

        logger.info("Capability '%s' successfully retired (Terminal state reached)", cap_id)
        return True, f"Capability '{cap_id}' retired permanently"

    def get_deprecation_plan(self, capability_id: str) -> Optional[DeprecationPlan]:
        return self._plans.get(capability_id)


_global_deprecation_manager: Optional[CapabilityDeprecationManager] = None


def get_deprecation_manager() -> CapabilityDeprecationManager:
    global _global_deprecation_manager
    if _global_deprecation_manager is None:
        _global_deprecation_manager = CapabilityDeprecationManager()
    return _global_deprecation_manager
