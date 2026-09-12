"""Cognitive Budget Engine: multi-scope hierarchical cognitive limits and lifecycle management (Task 77)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.orchestration.economy_schemas import (
    BudgetLifecycleState,
    BudgetScope,
    CognitiveBudget,
    CognitiveDimension,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CognitiveBudgetEngine:
    """Manages hierarchical cognitive budgets across Request, Session, Project, User, and Global scopes."""

    def __init__(self) -> None:
        # Key: (scope.value, scope_id) -> CognitiveBudget
        self._budgets: dict[tuple[str, str], CognitiveBudget] = {}
        self._init_default_global_budget()

    def _init_default_global_budget(self) -> None:
        """Initialize standard global cognitive budget."""
        global_limits = {
            CognitiveDimension.CONTEXT_TOKENS.value: 1_000_000.0,
            CognitiveDimension.MODEL_CALLS.value: 10_000.0,
            CognitiveDimension.REASONING_DEPTH.value: 100.0,
            CognitiveDimension.DELIBERATION_TIME_MS.value: 3_600_000.0,
            CognitiveDimension.AGENT_SLOTS.value: 50.0,
            CognitiveDimension.SIMULATION_BUDGET.value: 500.0,
            CognitiveDimension.TOOL_EXECUTIONS.value: 5_000.0,
        }
        self.create_budget(
            scope=BudgetScope.GLOBAL,
            scope_id="global",
            limits=global_limits,
            near_limit_threshold=0.85,
        )

    def create_budget(
        self,
        scope: BudgetScope,
        scope_id: str,
        limits: dict[str, float],
        near_limit_threshold: float = 0.85,
        reset_frequency: str = "NEVER",
        expires_at: datetime | None = None,
    ) -> CognitiveBudget:
        """Create and activate a new cognitive budget."""
        key = (scope.value, scope_id)
        budget = CognitiveBudget(
            budget_id=f"bg_{uuid.uuid4().hex[:8]}",
            scope=scope,
            scope_id=scope_id,
            state=BudgetLifecycleState.ACTIVE,
            limits=dict(limits),
            consumed={k: 0.0 for k in limits},
            reserved={k: 0.0 for k in limits},
            near_limit_threshold=near_limit_threshold,
            reset_frequency=reset_frequency,
            expires_at=expires_at,
            created_at=_now_utc(),
            updated_at=_now_utc(),
        )
        self._budgets[key] = budget
        logger.info("Cognitive budget created for scope=%s, scope_id=%s", scope.value, scope_id)
        return budget

    def get_budget(self, scope: BudgetScope, scope_id: str) -> CognitiveBudget | None:
        """Retrieve a specific budget by scope and identifier."""
        return self._budgets.get((scope.value, scope_id))

    def list_budgets(self) -> list[CognitiveBudget]:
        """List all registered cognitive budgets."""
        return list(self._budgets.values())

    def check_budget(
        self,
        demands: dict[str, float],
        scopes: list[tuple[BudgetScope, str]],
    ) -> tuple[bool, str, list[str]]:
        """Check if requested cognitive dimensions can be accommodated across all specified scopes.

        Returns (allowed, failure_reason, near_limit_dimensions).
        """
        near_limit_dims: set[str] = set()

        for scope, scope_id in scopes:
            budget = self.get_budget(scope, scope_id)
            if budget is None:
                # If non-global scope has no budget defined, it inherits without local limit
                continue

            if budget.state in (BudgetLifecycleState.EXHAUSTED, BudgetLifecycleState.SUSPENDED, BudgetLifecycleState.EXPIRED):
                return False, f"Budget for scope {scope.value}:{scope_id} is {budget.state.value}", []

            for dim_name, requested_amount in demands.items():
                limit = budget.limits.get(dim_name, float("inf"))
                consumed = budget.consumed.get(dim_name, 0.0)
                reserved = budget.reserved.get(dim_name, 0.0)
                projected = consumed + reserved + requested_amount

                if projected > limit:
                    return (
                        False,
                        f"Scope {scope.value}:{scope_id} exceeds dimension '{dim_name}': "
                        f"projected {projected:.1f} > limit {limit:.1f}",
                        list(near_limit_dims),
                    )

                if limit > 0 and (projected / limit) >= budget.near_limit_threshold:
                    near_limit_dims.add(f"{scope.value}:{dim_name}")

        return True, "All cognitive budgets verified", list(near_limit_dims)

    def allocate_budget(
        self,
        demands: dict[str, float],
        scopes: list[tuple[BudgetScope, str]],
    ) -> bool:
        """Atomically deduct cognitive demands from all matching scopes."""
        allowed, reason, _ = self.check_budget(demands, scopes)
        if not allowed:
            logger.warning("COGNITIVE_BUDGET_REJECTED: %s", reason)
            return False

        # Apply deductions
        for scope, scope_id in scopes:
            budget = self.get_budget(scope, scope_id)
            if budget is None:
                continue

            for dim_name, amount in demands.items():
                current = budget.consumed.get(dim_name, 0.0)
                budget.consumed[dim_name] = current + amount

            budget.updated_at = _now_utc()
            self._update_lifecycle_state(budget)

        return True

    def reserve_budget(
        self,
        demands: dict[str, float],
        scopes: list[tuple[BudgetScope, str]],
    ) -> bool:
        """Place a reservation hold on cognitive dimensions."""
        allowed, reason, _ = self.check_budget(demands, scopes)
        if not allowed:
            return False

        for scope, scope_id in scopes:
            budget = self.get_budget(scope, scope_id)
            if budget is None:
                continue

            for dim_name, amount in demands.items():
                current = budget.reserved.get(dim_name, 0.0)
                budget.reserved[dim_name] = current + amount

            budget.updated_at = _now_utc()
            self._update_lifecycle_state(budget)

        return True

    def release_reservation(
        self,
        demands: dict[str, float],
        scopes: list[tuple[BudgetScope, str]],
    ) -> None:
        """Release a reservation hold without consuming."""
        for scope, scope_id in scopes:
            budget = self.get_budget(scope, scope_id)
            if budget is None:
                continue

            for dim_name, amount in demands.items():
                current = budget.reserved.get(dim_name, 0.0)
                budget.reserved[dim_name] = max(0.0, current - amount)

            budget.updated_at = _now_utc()
            self._update_lifecycle_state(budget)

    def reset_budget(self, scope: BudgetScope, scope_id: str) -> bool:
        """Reset a budget's consumed and reserved counters, returning it to ACTIVE."""
        budget = self.get_budget(scope, scope_id)
        if budget is None:
            return False

        budget.state = BudgetLifecycleState.RESET
        for k in budget.consumed:
            budget.consumed[k] = 0.0
        for k in budget.reserved:
            budget.reserved[k] = 0.0

        budget.state = BudgetLifecycleState.ACTIVE
        budget.updated_at = _now_utc()
        logger.info("Budget reset: scope=%s, scope_id=%s", scope.value, scope_id)
        return True

    def _update_lifecycle_state(self, budget: CognitiveBudget) -> None:
        """Evaluate and transition budget lifecycle states based on consumption."""
        is_exhausted = False
        is_near_limit = False

        for dim_name, limit in budget.limits.items():
            used = budget.consumed.get(dim_name, 0.0) + budget.reserved.get(dim_name, 0.0)
            if limit > 0:
                ratio = used / limit
                if ratio >= 1.0:
                    is_exhausted = True
                    break
                elif ratio >= budget.near_limit_threshold:
                    is_near_limit = True

        if is_exhausted:
            budget.state = BudgetLifecycleState.EXHAUSTED
        elif is_near_limit:
            budget.state = BudgetLifecycleState.NEAR_LIMIT
        else:
            budget.state = BudgetLifecycleState.ACTIVE


default_budget_engine = CognitiveBudgetEngine()
