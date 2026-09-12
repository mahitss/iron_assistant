"""FastAPI REST API router for Kairo Resource & Capability Orchestration Engine (Task 59)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.orchestration.safety import (
    AuthorizationMissingError,
    CapabilityUnavailableError,
    OrchestrationSafetyError,
    ResourceContentionError,
    StaleOrchestrationError,
)
from app.orchestration.schemas import (
    CapabilityDefinition,
    CapabilityStatus,
    OrchestrationPlan,
    OrchestrationStatus,
    ProviderAssignment,
    ResourceDefinition,
    ResourceReservation,
    ResourceType,
)
from app.orchestration.service import orchestration_service

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


# Request Schemas
class AnalyzeRequest(BaseModel):
    tasks: list[dict[str, Any]]
    environment: str = "development"
    granted_permissions: list[str] = Field(default_factory=list)


class CreateOrchestrationRequest(BaseModel):
    name: str
    tasks: list[dict[str, Any]]
    strategic_plan_id: str | None = None
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    environment: str = "development"
    granted_permissions: list[str] = Field(default_factory=list)
    actor: str = "SYSTEM_USER"


class ReserveResourceRequest(BaseModel):
    resource_id: str
    owner: str
    purpose: str
    amount: float = 1.0
    expires_at: datetime
    scope: str = "GLOBAL"


class ReleaseReservationRequest(BaseModel):
    reservation_id: str


class RevalidateRequest(BaseModel):
    environment: str = "development"
    active_permissions: list[str] = Field(default_factory=list)
    unhealthy_providers: list[str] = Field(default_factory=list)


class FailoverRequest(BaseModel):
    task_id: str
    error_message: str
    actor: str = "SYSTEM_USER"


# Endpoints
@router.post("/analyze")
async def analyze_orchestration(req: AnalyzeRequest) -> dict[str, Any]:
    """Perform pre-execution gap analysis: capabilities, resources, permissions, and feasibility."""
    try:
        return await orchestration_service.analyze(
            tasks=req.tasks,
            environment=req.environment,
            granted_permissions=set(req.granted_permissions),
        )
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_model=OrchestrationPlan)
async def create_orchestration_plan(req: CreateOrchestrationRequest) -> OrchestrationPlan:
    """Transform tasks into a fully mapped OrchestrationPlan."""
    try:
        return await orchestration_service.create_orchestration_plan(
            name=req.name,
            tasks=req.tasks,
            strategic_plan_id=req.strategic_plan_id,
            dependencies=req.dependencies,
            environment=req.environment,
            granted_permissions=set(req.granted_permissions),
            actor=req.actor,
        )
    except CapabilityUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationMissingError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ResourceContentionError, OrchestrationSafetyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/catalog/capabilities", response_model=list[CapabilityDefinition])
async def list_capabilities(
    environment: str | None = None,
    status: CapabilityStatus | None = None,
) -> list[CapabilityDefinition]:
    """List registered capabilities in the system catalog."""
    return await orchestration_service.get_capabilities(environment=environment, status=status)


@router.get("/catalog/resources", response_model=list[ResourceDefinition])
async def list_resources(
    environment: str | None = None,
    resource_type: ResourceType | None = None,
) -> list[ResourceDefinition]:
    """List available resources, quotas, and capacity metrics."""
    return await orchestration_service.get_resources(environment=environment, resource_type=resource_type)


@router.post("/resources/reserve", response_model=ResourceReservation)
async def reserve_resource(req: ReserveResourceRequest) -> ResourceReservation:
    """Create a time-bounded resource reservation."""
    try:
        return await orchestration_service.reserve_resource(
            resource_id=req.resource_id,
            owner=req.owner,
            purpose=req.purpose,
            amount=req.amount,
            expires_at=req.expires_at,
            scope=req.scope,
        )
    except ResourceContentionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resources/release")
async def release_reservation(req: ReleaseReservationRequest) -> dict[str, Any]:
    """Release a resource reservation and restore capacity."""
    success = await orchestration_service.release_reservation(req.reservation_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Reservation '{req.reservation_id}' not found or already inactive.")
    return {"status": "RELEASED", "reservation_id": req.reservation_id}


@router.get("/list", response_model=list[OrchestrationPlan])
async def list_orchestration_plans(
    status: OrchestrationStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OrchestrationPlan]:
    """List recent orchestration plans."""
    return await orchestration_service.list_orchestrations(status=status, limit=limit)


@router.get("/{orchestration_id}", response_model=OrchestrationPlan)
async def get_orchestration_plan(orchestration_id: str) -> OrchestrationPlan:
    """Retrieve an orchestration plan by ID."""
    try:
        return await orchestration_service.get_orchestration_plan(orchestration_id)
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{orchestration_id}/assignments", response_model=list[ProviderAssignment])
async def get_plan_assignments(orchestration_id: str) -> list[ProviderAssignment]:
    """Retrieve task-to-provider assignments for an orchestration plan."""
    try:
        plan = await orchestration_service.get_orchestration_plan(orchestration_id)
        return plan.assignments
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{orchestration_id}/topology")
async def get_plan_topology(orchestration_id: str) -> dict[str, Any]:
    """Retrieve execution graph topology, waves, and synchronization barriers."""
    try:
        plan = await orchestration_service.get_orchestration_plan(orchestration_id)
        return {
            "orchestration_id": plan.orchestration_id,
            "task_graph": plan.task_graph,
            "execution_waves": plan.execution_waves,
            "synchronization_points": plan.synchronization_points,
            "verification_points": plan.verification_points,
            "fallback_paths": plan.fallback_paths,
        }
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{orchestration_id}/revalidate")
async def revalidate_plan(orchestration_id: str, req: RevalidateRequest) -> dict[str, Any]:
    """Revalidate plan before execution against environmental drift."""
    try:
        is_valid = await orchestration_service.revalidate(
            orchestration_id=orchestration_id,
            current_environment=req.environment,
            active_permissions=set(req.active_permissions),
        )
        return {"status": "VALIDATED", "is_valid": is_valid}
    except StaleOrchestrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{orchestration_id}/failover")
async def trigger_plan_failover(orchestration_id: str, req: FailoverRequest) -> dict[str, Any]:
    """Trigger failover for a failed task to secondary/emergency fallback."""
    try:
        return await orchestration_service.trigger_failover(
            orchestration_id=orchestration_id,
            task_id=req.task_id,
            error_message=req.error_message,
            actor=req.actor,
        )
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{orchestration_id}/health")
async def get_plan_health(orchestration_id: str) -> dict[str, Any]:
    """Get operational health status and resource leak audit report."""
    try:
        plan = await orchestration_service.get_orchestration_plan(orchestration_id)
        leaks = orchestration_service._engine.resource_registry.detect_leaks()
        return {
            "orchestration_id": plan.orchestration_id,
            "status": plan.status.value,
            "health": plan.health.value,
            "detected_leaks": leaks,
            "is_clean": len(leaks) == 0,
        }
    except OrchestrationSafetyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/explain/{task_id}")
async def explain_task_assignment(task_id: str) -> dict[str, Any]:
    """Explain why a specific provider and resource allocation was selected for a task."""
    return orchestration_service.explain_task(task_id)


@router.get("/audit/trail")
async def get_audit_trail(
    orchestration_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Retrieve immutable cryptographic audit trail events."""
    return orchestration_service.get_audit_trail(orchestration_id=orchestration_id, limit=limit)


# ==============================================================================
# Task 77 — Autonomous Resource Economy & Cognitive Budget Endpoints
# ==============================================================================

from app.orchestration.coordinator import default_economy_coordinator
from app.orchestration.economy_schemas import (
    BudgetLifecycleState,
    BudgetScope,
    CognitiveBudget,
    CognitiveDimension,
    DeadlockCycle,
    DegradationTier,
    EconomyStatusSummary,
    FairnessMetrics,
    PreemptionPolicy,
    PreemptionState,
    ResourceDemand,
    TaskPreemptionRecord,
    TradeOffEvaluation,
)


class EstimateDemandRequest(BaseModel):
    task_id: str
    resource_id: str
    capability_id: str = ""
    estimated_tokens: int = 1000
    model_calls: int = 1
    expected_time_s: float = 1.0
    priority: int = 1
    uncertainty_pct: float = 0.15
    confidence: float = 0.85
    is_preemptible: bool = True


class CreateBudgetRequest(BaseModel):
    scope: BudgetScope = BudgetScope.PROJECT
    scope_id: str
    limits: dict[str, float]
    near_limit_threshold: float = 0.85
    reset_frequency: str = "NEVER"


class CheckBudgetRequest(BaseModel):
    demands: dict[str, float]
    scopes: list[list[str]]  # e.g. [["PROJECT", "proj_alpha"], ["GLOBAL", "global"]]


class AllocateBudgetRequest(BaseModel):
    task_id: str
    demands: dict[str, float]
    scopes: list[list[str]]
    user_id: str = "default_user"
    priority: int = 1


class ResetBudgetRequest(BaseModel):
    scope: BudgetScope
    scope_id: str


class RequestPreemptionRequest(BaseModel):
    task_id: str
    preempted_by_task_id: str
    requestor_priority: int
    user_id: str = "default_user"
    policy: PreemptionPolicy = PreemptionPolicy.COOPERATIVE


class CheckpointTaskRequest(BaseModel):
    task_id: str
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    saved_context_tokens: int = 0
    cost_of_preemption: float = 0.0


class EvaluateTradeOffRequest(BaseModel):
    candidate_id: str
    quality_score: float = 1.0
    latency_ms: float = 100.0
    financial_cost: float = 0.01
    risk_score: float = 0.1
    resource_usage_score: float = 0.5
    degradation_tier: DegradationTier = DegradationTier.FULL_FIDELITY


class RouteModelRequest(BaseModel):
    task_id: str
    capability: str = "general"
    scopes: list[list[str]] | None = None


@router.get("/economy/overview", response_model=EconomyStatusSummary)
async def get_economy_overview() -> EconomyStatusSummary:
    """Retrieve consolidated overview of resource capacities, budgets, and saturation."""
    return default_economy_coordinator.get_economy_overview()


@router.post("/economy/demand/estimate", response_model=ResourceDemand)
async def estimate_demand(req: EstimateDemandRequest) -> ResourceDemand:
    """Estimate task resource demands under uncertainty with historical variance bounds."""
    return default_economy_coordinator.economy.estimate_demand(
        task_id=req.task_id,
        resource_id=req.resource_id,
        capability_id=req.capability_id,
        estimated_tokens=req.estimated_tokens,
        model_calls=req.model_calls,
        expected_time_s=req.expected_time_s,
        priority=req.priority,
        uncertainty_pct=req.uncertainty_pct,
        confidence=req.confidence,
        is_preemptible=req.is_preemptible,
    )


@router.post("/budgets/create", response_model=CognitiveBudget)
async def create_budget(req: CreateBudgetRequest) -> CognitiveBudget:
    """Create and register a multi-dimensional cognitive budget for a given scope."""
    return default_economy_coordinator.budget.create_budget(
        scope=req.scope,
        scope_id=req.scope_id,
        limits=req.limits,
        near_limit_threshold=req.near_limit_threshold,
        reset_frequency=req.reset_frequency,
    )


@router.get("/budgets", response_model=list[CognitiveBudget])
async def list_budgets() -> list[CognitiveBudget]:
    """List all registered cognitive budgets."""
    return default_economy_coordinator.budget.list_budgets()


@router.get("/budgets/{scope}/{scope_id}", response_model=CognitiveBudget)
async def get_budget(scope: BudgetScope, scope_id: str) -> CognitiveBudget:
    """Get cognitive budget for a specific scope and identifier."""
    b = default_economy_coordinator.budget.get_budget(scope, scope_id)
    if b is None:
        raise HTTPException(status_code=404, detail=f"Budget for {scope.value}:{scope_id} not found")
    return b


@router.post("/budgets/check")
async def check_budget(req: CheckBudgetRequest) -> dict[str, Any]:
    """Check whether requested cognitive units can be accommodated without exceeding limits."""
    parsed_scopes = [(BudgetScope(s[0]), s[1]) for s in req.scopes]
    allowed, reason, near_limits = default_economy_coordinator.budget.check_budget(req.demands, parsed_scopes)
    return {
        "allowed": allowed,
        "reason": reason,
        "near_limit_dimensions": near_limits,
    }


@router.post("/budgets/allocate")
async def allocate_budget(req: AllocateBudgetRequest) -> dict[str, Any]:
    """Atomically consume cognitive budget across scopes, obeying EmergencyStop."""
    parsed_scopes = [(BudgetScope(s[0]), s[1]) for s in req.scopes]
    success, reason, meta = default_economy_coordinator.request_allocation(
        task_id=req.task_id,
        demands=req.demands,
        scopes=parsed_scopes,
        user_id=req.user_id,
        priority=req.priority,
    )
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ALLOCATED", "reason": reason, "metadata": meta}


@router.post("/budgets/reset")
async def reset_budget(req: ResetBudgetRequest) -> dict[str, Any]:
    """Reset consumed counters on a cognitive budget."""
    success = default_economy_coordinator.budget.reset_budget(req.scope, req.scope_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Budget for {req.scope.value}:{req.scope_id} not found")
    return {"status": "RESET", "scope": req.scope.value, "scope_id": req.scope_id}


@router.post("/preempt", response_model=TaskPreemptionRecord)
async def request_preemption(req: RequestPreemptionRequest) -> TaskPreemptionRecord:
    """Request cooperative or immediate preemption of a lower-priority task."""
    success, reason, record = default_economy_coordinator.request_safe_preemption(
        task_id=req.task_id,
        preempted_by_task_id=req.preempted_by_task_id,
        requestor_priority=req.requestor_priority,
        user_id=req.user_id,
        policy=req.policy,
    )
    if not success or record is None:
        raise HTTPException(status_code=400, detail=reason)
    return record


@router.post("/checkpoint", response_model=TaskPreemptionRecord)
async def checkpoint_task(req: CheckpointTaskRequest) -> TaskPreemptionRecord:
    """Checkpoint task execution state and pause it."""
    return default_economy_coordinator.preemption.checkpoint_task(
        task_id=req.task_id,
        state_snapshot=req.state_snapshot,
        saved_context_tokens=req.saved_context_tokens,
        cost_of_preemption=req.cost_of_preemption,
    )


@router.post("/resume/{task_id}")
async def resume_task(task_id: str) -> dict[str, Any]:
    """Resume a preempted task from its checkpoint."""
    success, msg, snapshot = default_economy_coordinator.preemption.resume_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "RESUMED", "task_id": task_id, "snapshot": snapshot}


@router.get("/preemptions", response_model=list[TaskPreemptionRecord])
async def list_preemptions() -> list[TaskPreemptionRecord]:
    """List all currently paused, checkpointed, or preemption-requested tasks."""
    return default_economy_coordinator.preemption.list_preempted_tasks()


@router.get("/deadlock/detect", response_model=list[DeadlockCycle])
async def detect_deadlocks() -> list[DeadlockCycle]:
    """Detect cycles in the resource wait-for graph."""
    return default_economy_coordinator.deadlock.detect_deadlocks()


@router.post("/deadlock/resolve")
async def resolve_deadlocks() -> list[dict[str, Any]]:
    """Detect and resolve deadlock cycles boundedly."""
    return default_economy_coordinator.check_and_resolve_deadlocks()


@router.get("/fairness/metrics", response_model=FairnessMetrics)
async def get_fairness_metrics() -> FairnessMetrics:
    """Retrieve multi-tenant fair-share Gini coefficient and anti-starvation metrics."""
    budgets = default_economy_coordinator.budget.list_budgets()
    shares = {b.scope_id: sum(b.consumed.values()) for b in budgets}
    return default_economy_coordinator.fairness.compute_fairness_metrics(shares)


@router.post("/tradeoff/evaluate", response_model=TradeOffEvaluation)
async def evaluate_tradeoff(req: EvaluateTradeOffRequest) -> TradeOffEvaluation:
    """Evaluate multi-objective Pareto trade-offs across 5 objectives."""
    return default_economy_coordinator.tradeoff.evaluate_tradeoff(
        candidate_id=req.candidate_id,
        quality_score=req.quality_score,
        latency_ms=req.latency_ms,
        financial_cost=req.financial_cost,
        risk_score=req.risk_score,
        resource_usage_score=req.resource_usage_score,
        degradation_tier=req.degradation_tier,
    )


@router.post("/route-model")
async def route_model(req: RouteModelRequest) -> dict[str, Any]:
    """Select the optimal model for a task based on economy saturation and degradation tier."""
    parsed_scopes = [(BudgetScope(s[0]), s[1]) for s in req.scopes] if req.scopes else None
    model_id, tier = default_economy_coordinator.route_model_for_task(
        task_id=req.task_id,
        capability=req.capability,
        scopes=parsed_scopes,
    )
    return {"task_id": req.task_id, "selected_model": model_id, "degradation_tier": tier.value}
