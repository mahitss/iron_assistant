"""Pydantic v2 schemas and domain models for Kairo Autonomous Resource Economy,
Capability Allocation & Cognitive Budget Engine (Task 77).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BudgetScope(str, Enum):
    """Hierarchical scoping for cognitive budgets."""
    REQUEST = "REQUEST"
    SESSION = "SESSION"
    PROJECT = "PROJECT"
    USER = "USER"
    GLOBAL = "GLOBAL"


class BudgetLifecycleState(str, Enum):
    """7-state lifecycle of a cognitive budget."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    NEAR_LIMIT = "NEAR_LIMIT"
    EXHAUSTED = "EXHAUSTED"
    RESET = "RESET"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class CognitiveDimension(str, Enum):
    """Finite cognitive dimensions tracked by the budget engine."""
    REASONING_DEPTH = "REASONING_DEPTH"
    MODEL_CALLS = "MODEL_CALLS"
    CONTEXT_TOKENS = "CONTEXT_TOKENS"
    DELIBERATION_TIME_MS = "DELIBERATION_TIME_MS"
    AGENT_SLOTS = "AGENT_SLOTS"
    SIMULATION_BUDGET = "SIMULATION_BUDGET"
    TOOL_EXECUTIONS = "TOOL_EXECUTIONS"


class PreemptionState(str, Enum):
    """7-state lifecycle of a preemptible task."""
    RUNNING = "RUNNING"
    PREEMPTION_REQUESTED = "PREEMPTION_REQUESTED"
    CHECKPOINTING = "CHECKPOINTING"
    PAUSED = "PAUSED"
    RESUMABLE = "RESUMABLE"
    CANCELLED = "CANCELLED"
    RESUMED = "RESUMED"


class PreemptionPolicy(str, Enum):
    """Policies governing when and how a task can be preempted."""
    NEVER = "NEVER"
    COOPERATIVE = "COOPERATIVE"
    IMMEDIATE = "IMMEDIATE"
    ON_SATURATION = "ON_SATURATION"


class ContentionResolutionStrategy(str, Enum):
    """Strategies for resolving resource contention and deadlocks."""
    PRIORITIZE = "PRIORITIZE"
    SEQUENCE = "SEQUENCE"
    RESERVE = "RESERVE"
    SCALE = "SCALE"
    SUBSTITUTE = "SUBSTITUTE"
    DEFER = "DEFER"
    REPLAN = "REPLAN"
    PREEMPT = "PREEMPT"


class DegradationTier(str, Enum):
    """4-tier graceful degradation hierarchy."""
    FULL_FIDELITY = "FULL_FIDELITY"
    MODERATE_COMPRESSION = "MODERATE_COMPRESSION"
    AGGRESSIVE_THROTTLE = "AGGRESSIVE_THROTTLE"
    EMERGENCY_MINIMAL = "EMERGENCY_MINIMAL"


class SaturationState(str, Enum):
    """Saturation classification for resources and economy overall."""
    HEALTHY = "HEALTHY"
    SATURATED = "SATURATED"
    OVERCOMMITTED = "OVERCOMMITTED"


class ResourceDemand(BaseModel):
    """Task resource demand estimation with calibrated uncertainty."""
    model_config = ConfigDict(extra="ignore")

    demand_id: str = Field(default_factory=lambda: f"dem_{uuid.uuid4().hex[:8]}")
    task_id: str
    resource_id: str
    capability_id: str = ""
    estimated_tokens: int = Field(default=1000, ge=0)
    model_calls: int = Field(default=1, ge=0)
    expected_time_s: float = Field(default=1.0, ge=0.0)
    lower_bound: float = Field(default=0.0, ge=0.0)
    upper_bound: float = Field(default=0.0, ge=0.0)
    uncertainty_pct: float = Field(default=0.15, ge=0.0, le=1.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    priority: int = Field(default=1, ge=0)
    is_preemptible: bool = True
    created_at: datetime = Field(default_factory=_now_utc)


class CognitiveBudget(BaseModel):
    """Hierarchical multi-dimensional cognitive budget."""
    model_config = ConfigDict(extra="ignore")

    budget_id: str = Field(default_factory=lambda: f"bg_{uuid.uuid4().hex[:8]}")
    scope: BudgetScope = BudgetScope.GLOBAL
    scope_id: str = "global"
    state: BudgetLifecycleState = BudgetLifecycleState.CREATED
    limits: dict[str, float] = Field(default_factory=dict)
    consumed: dict[str, float] = Field(default_factory=dict)
    reserved: dict[str, float] = Field(default_factory=dict)
    near_limit_threshold: float = Field(default=0.85, ge=0.5, le=0.99)
    reset_frequency: str = "NEVER"  # HOURLY, DAILY, MONTHLY, NEVER
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class TaskPreemptionRecord(BaseModel):
    """Audit record for a task preemption event."""
    model_config = ConfigDict(extra="ignore")

    preemption_id: str = Field(default_factory=lambda: f"prm_{uuid.uuid4().hex[:8]}")
    task_id: str
    priority: int = 1
    preempted_by_task_id: str | None = None
    state: PreemptionState = PreemptionState.RUNNING
    checkpoint_token: str | None = None
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    saved_context_tokens: int = 0
    wait_time_s: float = 0.0
    cost_of_preemption: float = 0.0
    created_at: datetime = Field(default_factory=_now_utc)
    resumed_at: datetime | None = None


class DeadlockCycle(BaseModel):
    """Detected cycle in the resource wait-for graph."""
    model_config = ConfigDict(extra="ignore")

    cycle_id: str = Field(default_factory=lambda: f"dlk_{uuid.uuid4().hex[:8]}")
    involved_tasks: list[str] = Field(default_factory=list)
    involved_resources: list[str] = Field(default_factory=list)
    detection_timestamp: datetime = Field(default_factory=_now_utc)
    resolution_strategy: str = ContentionResolutionStrategy.PREEMPT.value
    victim_task_id: str | None = None
    resolved: bool = False


class TradeOffEvaluation(BaseModel):
    """Multi-objective Pareto evaluation across 5 dimensions."""
    model_config = ConfigDict(extra="ignore")

    evaluation_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    candidate_id: str
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    latency_ms: float = Field(default=100.0, ge=0.0)
    financial_cost: float = Field(default=0.0, ge=0.0)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_usage_score: float = Field(default=0.5, ge=0.0, le=1.0)
    composite_score: float = Field(default=0.75, ge=0.0, le=1.0)
    degradation_tier: DegradationTier = DegradationTier.FULL_FIDELITY
    rationale: str = ""


class FairnessMetrics(BaseModel):
    """Fairness and anti-starvation measurement."""
    model_config = ConfigDict(extra="ignore")

    gini_coefficient: float = Field(default=0.0, ge=0.0, le=1.0)
    max_min_ratio: float = Field(default=1.0, ge=0.0)
    starvation_count: int = 0
    average_wait_time_s: float = 0.0
    longest_waiting_task_id: str | None = None
    aging_boost_active_count: int = 0
    calculated_at: datetime = Field(default_factory=_now_utc)


class EconomyStatusSummary(BaseModel):
    """Master health summary of the resource economy."""
    model_config = ConfigDict(extra="ignore")

    total_resources: int = 0
    capacity_saturation_pct: float = 0.0
    saturation_state: SaturationState = SaturationState.HEALTHY
    active_budgets_count: int = 0
    exhausted_budgets_count: int = 0
    preempted_tasks_count: int = 0
    active_deadlocks_count: int = 0
    fairness_gini: float = 0.0
    active_degradation_tier: DegradationTier = DegradationTier.FULL_FIDELITY
    timestamp: datetime = Field(default_factory=_now_utc)
