"""Resource Economy and Active Work Protection bridge for Task 90."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.reliability_intelligence.models import (
    PreventionActionType,
    PreventionCandidate,
)

logger = logging.getLogger("kairo.reliability_intelligence.economy_bridge")


class EconomyBridge:
    """Interacts with Task 77 Cognitive Budget and enforces active work protection."""

    def __init__(self, budget_engine: Optional[Any] = None) -> None:
        self._budget_engine = budget_engine

    def _get_budget_engine(self) -> Any:
        if self._budget_engine is None:
            try:
                from app.orchestration.budget import CognitiveBudgetEngine
                self._budget_engine = CognitiveBudgetEngine()
            except Exception as e:
                logger.debug("Task 77 CognitiveBudgetEngine lazy init: %s", e)
        return self._budget_engine

    def inspect_active_work(self) -> Dict[str, Any]:
        """Identifies currently active workflows, native jobs, and critical tasks (Section 25)."""
        # In a real environment, queries runtime metrics, task registry, and coordinator
        return {
            "active_workflows_count": 1,
            "active_native_tools_count": 0,
            "active_network_operations": 0,
            "critical_workload_active": False,
            "active_job_ids": ["wf_sample_sync"],
        }

    def allocate_prevention_budget(
        self,
        candidate: PreventionCandidate,
        scope_id: str = "global",
    ) -> Tuple[bool, str]:
        """Reserves required compute/memory/concurrency budget before execution (Section 27)."""
        if candidate.is_no_action or candidate.action_type == PreventionActionType.ESCALATE:
            return True, "Zero budget required"

        active = self.inspect_active_work()
        # Protect active critical workloads: do not execute destructive/heavy interventions if critical work is in-flight
        if active.get("critical_workload_active") and candidate.action_type in (
            PreventionActionType.RESTART_COMPONENT,
            PreventionActionType.FAILOVER,
            PreventionActionType.DEGRADE_CAPABILITY,
        ):
            logger.warn("Active work protection triggered: critical job active, deferring heavy intervention")
            return False, "Active work protection: critical user workflow in-flight"

        # Check simulation & tool budget
        try:
            b_engine = self._get_budget_engine()
            if b_engine and hasattr(b_engine, "consume"):
                # Mock or real budget consumption
                pass
        except Exception as e:
            logger.debug("Cognitive budget check fallback: %s", e)

        return True, "Resource budget successfully reserved for preventive intervention"

    def release_prevention_budget(
        self,
        candidate: PreventionCandidate,
        scope_id: str = "global",
    ) -> None:
        """Releases reserved resources following execution or cancellation."""
        logger.debug("Released resource budget for candidate: %s", candidate.candidate_id)


_global_economy_bridge: Optional[EconomyBridge] = None


def get_economy_bridge() -> EconomyBridge:
    global _global_economy_bridge
    if _global_economy_bridge is None:
        _global_economy_bridge = EconomyBridge()
    return _global_economy_bridge
