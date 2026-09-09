"""Runtime budget enforcement and tracking for autonomous tasks (Spec 14, 15, 73, 99)."""

import time
from app.config.settings import get_settings
from app.tasks.schemas import TaskBudget


class BudgetExceededError(RuntimeError):
    """Raised when an autonomous task exhausts any allocated budget dimension."""

    def __init__(self, dimension: str, limit: float | int, current: float | int) -> None:
        super().__init__(
            f"BUDGET_EXCEEDED: Task exceeded {dimension} budget (limit: {limit}, used: {current})"
        )
        self.dimension = dimension
        self.limit = limit
        self.current = current


class TaskBudgetEnforcer:
    """Strict runtime enforcer for autonomous task execution budgets."""

    def __init__(self, budget: TaskBudget | None = None) -> None:
        settings = get_settings()
        if budget is not None:
            self.budget = budget
        else:
            self.budget = TaskBudget(
                max_steps=getattr(settings, "KAIRO_TASK_MAX_STEPS", 20),
                max_tool_calls=getattr(settings, "KAIRO_TASK_MAX_TOOL_CALLS", 50),
                max_agents=getattr(settings, "KAIRO_TASK_MAX_AGENTS", 5),
                max_duration_seconds=getattr(settings, "KAIRO_TASK_MAX_DURATION", 1800),
                max_cost_usd=getattr(settings, "KAIRO_TASK_MAX_COST", 10.0),
                max_replans=getattr(settings, "KAIRO_TASK_MAX_REPLANS", 5),
            )
        self._start_time = time.monotonic()

    @property
    def current_budget(self) -> TaskBudget:
        """Return the current budget state with updated elapsed duration."""
        elapsed = time.monotonic() - self._start_time
        self.budget.duration_used_seconds = round(elapsed, 2)
        return self.budget

    def check_limits(self) -> None:
        """Evaluate all budget limits and raise BudgetExceededError if exhausted."""
        b = self.current_budget
        exhausted, reason = b.is_exhausted()
        if exhausted:
            if b.steps_used > b.max_steps:
                raise BudgetExceededError("step", b.max_steps, b.steps_used)
            if b.tool_calls_used > b.max_tool_calls:
                raise BudgetExceededError("tool_call", b.max_tool_calls, b.tool_calls_used)
            if b.agents_used > b.max_agents:
                raise BudgetExceededError("agent", b.max_agents, b.agents_used)
            if b.duration_used_seconds > b.max_duration_seconds:
                raise BudgetExceededError("duration_seconds", b.max_duration_seconds, b.duration_used_seconds)
            if b.cost_used_usd > b.max_cost_usd:
                raise BudgetExceededError("cost_usd", b.max_cost_usd, b.cost_used_usd)
            if b.replans_used > b.max_replans:
                raise BudgetExceededError("replan", b.max_replans, b.replans_used)
            raise BudgetExceededError("general", 0, 0)

    def record_step(self, count: int = 1) -> None:
        """Increment executed step counter and enforce limits."""
        self.budget.steps_used += count
        self.check_limits()

    def record_tool_calls(self, count: int = 1) -> None:
        """Increment tool call counter and enforce limits."""
        self.budget.tool_calls_used += count
        self.check_limits()

    def record_agent_call(self, count: int = 1) -> None:
        """Increment spawned agent counter and enforce limits."""
        self.budget.agents_used += count
        self.check_limits()

    def record_cost(self, cost_usd: float) -> None:
        """Accumulate estimated execution cost and enforce limits."""
        self.budget.cost_used_usd = round(self.budget.cost_used_usd + cost_usd, 4)
        self.check_limits()

    def record_replan(self, count: int = 1) -> None:
        """Increment replan count and enforce limits."""
        self.budget.replans_used += count
        self.check_limits()
