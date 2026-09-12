"""Master Resource Economy Coordinator: unifying budgets, preemption, deadlock, fairness, and safety (Task 77)."""

from __future__ import annotations

import logging
from typing import Any

from app.models.router import get_model_router
from app.orchestration.budget import CognitiveBudgetEngine, default_budget_engine
from app.orchestration.deadlock import DeadlockContentionEngine, default_deadlock_engine
from app.orchestration.economy import ResourceEconomyEngine, default_economy_engine
from app.orchestration.economy_schemas import (
    BudgetScope,
    CognitiveBudget,
    DegradationTier,
    EconomyStatusSummary,
    FairnessMetrics,
    PreemptionPolicy,
    PreemptionState,
    SaturationState,
    TaskPreemptionRecord,
    TradeOffEvaluation,
)
from app.orchestration.fairness import FairnessEngine, default_fairness_engine
from app.orchestration.preemption import TaskPreemptionEngine, default_preemption_engine
from app.orchestration.tradeoff import ResourceTradeOffEngine, default_tradeoff_engine
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service

logger = logging.getLogger(__name__)


class ResourceEconomyCoordinator:
    """Master facade coordinating the autonomous resource economy, cognitive budgets, and safety invariants."""

    def __init__(
        self,
        economy_engine: ResourceEconomyEngine | None = None,
        budget_engine: CognitiveBudgetEngine | None = None,
        preemption_engine: TaskPreemptionEngine | None = None,
        deadlock_engine: DeadlockContentionEngine | None = None,
        fairness_engine: FairnessEngine | None = None,
        tradeoff_engine: ResourceTradeOffEngine | None = None,
        emergency_stop_service: EmergencyStopService | None = None,
    ) -> None:
        self.economy = economy_engine or default_economy_engine
        self.budget = budget_engine or default_budget_engine
        self.preemption = preemption_engine or default_preemption_engine
        self.deadlock = deadlock_engine or default_deadlock_engine
        self.fairness = fairness_engine or default_fairness_engine
        self.tradeoff = tradeoff_engine or default_tradeoff_engine
        self.emergency_stop = emergency_stop_service or get_emergency_stop_service()

    def is_stopped(self, user_id: str = "default_user") -> bool:
        """Check if EmergencyStop is active."""
        return self.emergency_stop.is_stopped(user_id)

    def request_allocation(
        self,
        task_id: str,
        demands: dict[str, float],
        scopes: list[tuple[BudgetScope, str]],
        user_id: str = "default_user",
        priority: int = 1,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Request allocation of cognitive dimensions across hierarchical scopes.

        Enforces:
        1. EmergencyStop check (fails immediately if active).
        2. Budget boundary enforcement across all scopes.
        3. Fair-share priority aging.
        """
        if self.is_stopped(user_id):
            logger.error("RESOURCE_ALLOCATION_HALTED: Emergency stop is active for user %s", user_id)
            return False, "Emergency stop is active: all resource allocations rejected", {}

        # Verify cognitive budget availability
        allowed, reason, near_limits = self.budget.check_budget(demands, scopes)
        if not allowed:
            return False, reason, {"near_limits": near_limits}

        # Deduct budget
        success = self.budget.allocate_budget(demands, scopes)
        if not success:
            return False, "Failed to atomically consume cognitive budget", {}

        # Register task for fairness tracking
        self.fairness.record_task_arrival(task_id)
        self.deadlock.register_task_priority(task_id, priority)
        self.preemption.register_task(task_id, priority)

        # Evaluate degradation tier recommendation
        sat_pct, _ = self.economy.compute_economy_saturation()
        tier = self.economy.recommend_degradation_tier(sat_pct)

        return True, "Allocation granted", {
            "tier": tier.value,
            "near_limits": near_limits,
            "saturation_pct": sat_pct,
        }

    def request_safe_preemption(
        self,
        task_id: str,
        preempted_by_task_id: str,
        requestor_priority: int,
        user_id: str = "default_user",
        policy: PreemptionPolicy = PreemptionPolicy.COOPERATIVE,
    ) -> tuple[bool, str, TaskPreemptionRecord | None]:
        """Safely request preemption of a task, strictly checking EmergencyStop and priority rules."""
        if self.is_stopped(user_id):
            return False, "Emergency stop active: preemption commands disabled", None

        return self.preemption.request_preemption(
            task_id=task_id,
            preempted_by_task_id=preempted_by_task_id,
            requestor_priority=requestor_priority,
            policy=policy,
        )

    def route_model_for_task(
        self,
        task_id: str,
        capability: str = "general",
        scopes: list[tuple[BudgetScope, str]] | None = None,
    ) -> tuple[str, DegradationTier]:
        """Select AI model based on current economy saturation and degradation tier."""
        sat_pct, _ = self.economy.compute_economy_saturation()
        tier = self.economy.recommend_degradation_tier(sat_pct)

        # Select model based on tier
        if tier == DegradationTier.FULL_FIDELITY:
            try:
                router = get_model_router()
                model_def = router.select_model(capability)
                return model_def.id, tier
            except Exception:
                return "openrouter/reasoning", tier
        elif tier == DegradationTier.MODERATE_COMPRESSION:
            return "openrouter/fast", tier
        elif tier == DegradationTier.AGGRESSIVE_THROTTLE:
            return "openrouter/free", tier
        else:
            return "system/deterministic_rule", tier

    def check_and_resolve_deadlocks(self) -> list[dict[str, Any]]:
        """Detect wait-for graph deadlocks and resolve them boundedly."""
        cycles = self.deadlock.detect_deadlocks()
        resolutions = []
        for cycle in cycles:
            victim, strategy = self.deadlock.resolve_deadlock(cycle)
            resolutions.append({
                "cycle_id": cycle.cycle_id,
                "victim_task_id": victim,
                "strategy": strategy.value,
                "involved_tasks": cycle.involved_tasks,
                "involved_resources": cycle.involved_resources,
            })
        return resolutions

    def get_economy_overview(self) -> EconomyStatusSummary:
        """Produce consolidated health summary across all resource subsystems."""
        resources = self.economy._registry.list_all()
        sat_pct, sat_state = self.economy.compute_economy_saturation()
        tier = self.economy.recommend_degradation_tier(sat_pct)
        budgets = self.budget.list_budgets()
        preempted = self.preemption.list_preempted_tasks()
        deadlocks = self.deadlock.detect_deadlocks()
        fairness = self.fairness.compute_fairness_metrics(
            tenant_shares={b.scope_id: sum(b.consumed.values()) for b in budgets}
        )

        active_count = sum(1 for b in budgets if b.state.value == "ACTIVE")
        exhausted_count = sum(1 for b in budgets if b.state.value == "EXHAUSTED")

        return EconomyStatusSummary(
            total_resources=len(resources),
            capacity_saturation_pct=sat_pct,
            saturation_state=sat_state,
            active_budgets_count=active_count,
            exhausted_budgets_count=exhausted_count,
            preempted_tasks_count=len(preempted),
            active_deadlocks_count=len(deadlocks),
            fairness_gini=fairness.gini_coefficient,
            active_degradation_tier=tier,
        )


default_economy_coordinator = ResourceEconomyCoordinator()
