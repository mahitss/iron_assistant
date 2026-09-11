"""FastAPI REST API router for Kairo Resilience, Circuit Breakers, and System Reliability."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.resilience.manager import resilience_manager
from app.resilience.schemas import (
    CircuitBreakerStatus,
    QuarantineRecord,
    RecoveryState,
    SystemReliabilityDashboard,
)

router = APIRouter(prefix="/resilience", tags=["Resilience & Fault-Tolerance"])


@router.get("/health", summary="Get system liveness, readiness, and dependency health")
async def get_health(session: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    """Probes critical dependencies and returns comprehensive health status."""
    # Probe real database and redis
    await resilience_manager.health_tracker.probe_database(session)
    await resilience_manager.health_tracker.probe_redis()

    is_alive, live_msg = resilience_manager.health_tracker.evaluate_liveness()
    is_ready, ready_msg = resilience_manager.health_tracker.evaluate_readiness()

    return {
        "liveness": {"alive": is_alive, "message": live_msg},
        "readiness": {"ready": is_ready, "message": ready_msg},
        "read_only_mode": resilience_manager.degradation_mgr.is_read_only_mode,
        "dependencies": [
            r.model_dump() for r in resilience_manager.health_tracker.get_all_reports()
        ],
    }


@router.get("/dashboard", response_model=SystemReliabilityDashboard, summary="System Reliability Dashboard metrics")
async def get_dashboard(session: AsyncSession = Depends(get_db_session)) -> SystemReliabilityDashboard:
    """Returns reliability metrics, circuit breaker states, and active quarantine counts."""
    # Refresh DB probe
    await resilience_manager.health_tracker.probe_database(session)
    return resilience_manager.get_reliability_dashboard()


@router.get("/circuits", response_model=list[CircuitBreakerStatus], summary="List all scoped circuit breakers")
async def list_circuits() -> list[CircuitBreakerStatus]:
    return resilience_manager.circuit_registry.list_all()


@router.post("/circuits/{circuit_id:path}/reset", summary="Reset a circuit breaker to CLOSED")
async def reset_circuit(circuit_id: str) -> dict[str, Any]:
    success = resilience_manager.circuit_registry.reset(circuit_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{circuit_id}' not found",
        )
    return {"status": "ok", "circuit_id": circuit_id, "state": "CLOSED"}


@router.get("/quarantine", response_model=list[QuarantineRecord], summary="List quarantined poison tasks")
async def list_quarantined(session: AsyncSession = Depends(get_db_session)) -> list[QuarantineRecord]:
    return await resilience_manager.quarantine_mgr.list_quarantined(session)


@router.post("/quarantine/{task_id}/release", summary="Operator release of a quarantined task")
async def release_quarantined_task(
    task_id: str,
    released_by: str = Query(default="operator"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    success = await resilience_manager.quarantine_mgr.release_task(
        task_id=task_id,
        released_by=released_by,
        session=session,
    )
    return {"status": "ok", "task_id": task_id, "released": success}


@router.post("/tasks/{task_id}/recover", summary="Evaluate and recover a task with No Blind Resume checks")
async def recover_task(
    task_id: str,
    worker_id: str = Query(default="worker-manual"),
    current_policy_version: int = Query(default=1),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    recovery_state, checkpoint = await resilience_manager.recovery_mgr.evaluate_and_recover(
        task_id=task_id,
        worker_id=worker_id,
        current_policy_version=current_policy_version,
        session=session,
    )
    return {
        "status": "ok",
        "task_id": task_id,
        "recovery_state": recovery_state,
        "checkpoint": checkpoint.model_dump() if checkpoint else None,
    }


@router.post("/degradation/read-only", summary="Toggle read-only degraded mode")
async def set_read_only_mode(enabled: bool = Query(...)) -> dict[str, Any]:
    resilience_manager.degradation_mgr.set_read_only_mode(enabled)
    return {"status": "ok", "read_only_mode": enabled}


# ============================================================================
# Task 76 Autonomous Resilience, Recovery, and Adaptive Defense Endpoints
# ============================================================================

from pydantic import BaseModel, Field
from app.resilience.intelligence import get_resilience_intelligence_coordinator
from app.resilience.defense_schemas import (
    ResilienceAssessment,
    RecoveryPlan,
    ResilienceGap,
    RecoveryPath,
    HumanHandoffPacket,
)


class AssessmentRequestPayload(BaseModel):
    scope: str = "SYSTEM"
    target: str = "CORE"
    topology: dict[str, Any] = Field(default_factory=lambda: {"nodes": {}, "edges": []})
    provenance: dict[str, Any] = Field(default_factory=dict)


class RecoveryPlanRequestPayload(BaseModel):
    incident_id: str | None = None
    cascade_path: list[str] = Field(default_factory=list)
    topology: dict[str, Any] = Field(default_factory=lambda: {"nodes": {}, "edges": []})
    uncertainty: float = 0.2


class ApprovalPayload(BaseModel):
    approved_by: str
    approval_id: str | None = None


class VerificationPayload(BaseModel):
    live_telemetry: dict[str, Any] = Field(default_factory=dict)


class AbortPayload(BaseModel):
    reason: str = "Operator aborted execution"


class HandoffPayload(BaseModel):
    incident_id: str
    reason: str = "Uncertainty exceeded autonomous threshold"


@router.post("/assess", response_model=ResilienceAssessment, summary="Autonomous resilience assessment and scorecard generation")
async def run_resilience_assessment(payload: AssessmentRequestPayload) -> ResilienceAssessment:
    coord = get_resilience_intelligence_coordinator()
    return coord.assess_resilience(
        scope=payload.scope,
        target=payload.target,
        topology=payload.topology,
        provenance=payload.provenance,
    )


@router.get("/overview", summary="Resilience overview dashboard metrics and active status")
async def get_resilience_overview() -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    trends = coord.adaptive_defense.calculate_resilience_trends()
    active_plans = [p for p in coord.recovery_plans.values() if p.state not in ("RECOVERED", "ABORTED", "ROLLED_BACK")]
    recent_assessments = list(coord.assessments.values())[-5:]
    latest = recent_assessments[-1] if recent_assessments else None

    return {
        "status": "HEALTHY" if not active_plans else "DEGRADED",
        "latest_assessment_id": latest.resilience_assessment_id if latest else None,
        "overall_resilience_index": latest.scorecard.overall_resilience_index if latest else 1.0,
        "bottlenecks": [b.value for b in latest.scorecard.bottleneck_dimensions] if latest else [],
        "active_recovery_plans_count": len(active_plans),
        "total_assessments": len(coord.assessments),
        "metrics": trends.model_dump(),
    }


@router.get("/bottlenecks", summary="Systemic bottlenecks and single points of failure")
async def get_system_bottlenecks() -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    recent = list(coord.assessments.values())[-1] if coord.assessments else None
    if not recent:
        return {"bottlenecks": [], "spofs": [], "gaps_count": 0}

    spof_gaps = [g for g in recent.gaps if g.gap_type.value in ("single_point_of_failure", "no_redundancy")]
    return {
        "bottlenecks": [b.value for b in recent.scorecard.bottleneck_dimensions],
        "spofs": [g.target_entity for g in spof_gaps],
        "gaps_count": len(recent.gaps),
        "critical_gaps": [g.model_dump() for g in spof_gaps],
    }


@router.get("/recovery-history", summary="Historical recovery performance, MTTR/MTTC/MTTD, and lessons")
async def get_recovery_history() -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    trends = coord.adaptive_defense.calculate_resilience_trends()
    return {
        "trends": trends.model_dump(),
        "incident_count": len(coord.adaptive_defense.incident_history),
        "lessons": [les.model_dump() for les in coord.adaptive_defense.lessons_store],
        "recommendations": [rec.model_dump() for rec in coord.adaptive_defense.recommendations_store],
    }


@router.get("/{assessment_id}", response_model=ResilienceAssessment, summary="Retrieve a resilience assessment by ID")
async def get_resilience_assessment(assessment_id: str) -> ResilienceAssessment:
    coord = get_resilience_intelligence_coordinator()
    ass = coord.assessments.get(assessment_id)
    if not ass:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return ass


@router.get("/{assessment_id}/gaps", response_model=list[ResilienceGap], summary="Retrieve identified resilience gaps")
async def get_assessment_gaps(assessment_id: str) -> list[ResilienceGap]:
    coord = get_resilience_intelligence_coordinator()
    ass = coord.assessments.get(assessment_id)
    if not ass:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return ass.gaps


@router.get("/{assessment_id}/recovery-paths", response_model=list[RecoveryPath], summary="Retrieve candidate recovery paths")
async def get_assessment_recovery_paths(assessment_id: str) -> list[RecoveryPath]:
    coord = get_resilience_intelligence_coordinator()
    ass = coord.assessments.get(assessment_id)
    if not ass:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return ass.recovery_paths


@router.get("/{assessment_id}/scenarios", summary="Simulated hypothetical failure scenarios and counterfactual comparisons")
async def get_assessment_scenarios(assessment_id: str) -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    ass = coord.assessments.get(assessment_id)
    if not ass:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")

    scenarios = []
    for g in ass.gaps:
        scenarios.append({
            "scenario_id": f"scen_{g.gap_id}",
            "target": g.target_entity,
            "failure_type": g.gap_type.value,
            "hypothetical": True,
            "simulated_cascade_depth": 3 if g.severity == "CRITICAL" else 1,
            "remediation_benefit": g.remediation_candidate,
        })
    return {"assessment_id": assessment_id, "scenarios": scenarios}


@router.get("/{assessment_id}/explanation", summary="Explanation rationale for resilience dimensions and bottlenecks")
async def get_assessment_explanation(assessment_id: str) -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    ass = coord.assessments.get(assessment_id)
    if not ass:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return {
        "assessment_id": assessment_id,
        "rationale": ass.scorecard.rationale,
        "bottlenecks": [b.value for b in ass.scorecard.bottleneck_dimensions],
        "overall_resilience_index": ass.scorecard.overall_resilience_index,
    }


@router.get("/{assessment_id}/provenance", summary="Provenance and evidence trail for assessment")
async def get_assessment_provenance(assessment_id: str) -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    ass = coord.assessments.get(assessment_id)
    if not ass:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return {
        "assessment_id": assessment_id,
        "provenance": ass.provenance,
        "assumptions": ass.assumptions,
        "assessment_time": ass.assessment_time,
    }


# ============================================================================
# Recovery Router and Endpoints
# ============================================================================

recovery_router = APIRouter(prefix="/recovery", tags=["Recovery & Containment"])


@recovery_router.post("/plan", response_model=RecoveryPlan, summary="Plan multi-strategy recovery and containment")
@router.post("/recovery/plan", response_model=RecoveryPlan, summary="Plan multi-strategy recovery (alias)")
async def plan_recovery(payload: RecoveryPlanRequestPayload) -> RecoveryPlan:
    coord = get_resilience_intelligence_coordinator()
    return coord.plan_containment_and_recovery(
        incident_id=payload.incident_id,
        cascade_path=payload.cascade_path,
        topology=payload.topology,
        uncertainty=payload.uncertainty,
    )


@recovery_router.get("/active", response_model=list[RecoveryPlan], summary="List active recovery plans")
@router.get("/recovery/active", response_model=list[RecoveryPlan], summary="List active recovery plans (alias)")
async def list_active_recovery_plans() -> list[RecoveryPlan]:
    coord = get_resilience_intelligence_coordinator()
    return [p for p in coord.recovery_plans.values() if p.state not in ("RECOVERED", "ABORTED")]


@recovery_router.get("/{plan_id}", response_model=RecoveryPlan, summary="Retrieve a recovery plan by ID")
@router.get("/recovery/{plan_id}", response_model=RecoveryPlan, summary="Retrieve a recovery plan by ID (alias)")
async def get_recovery_plan(plan_id: str) -> RecoveryPlan:
    coord = get_resilience_intelligence_coordinator()
    plan = coord.recovery_plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Recovery plan '{plan_id}' not found")
    return plan


@recovery_router.post("/{plan_id}/approve", response_model=RecoveryPlan, summary="Approve a recovery plan")
@router.post("/recovery/{plan_id}/approve", response_model=RecoveryPlan, summary="Approve a recovery plan (alias)")
async def approve_recovery_plan(plan_id: str, payload: ApprovalPayload) -> RecoveryPlan:
    coord = get_resilience_intelligence_coordinator()
    plan = coord.recovery_plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Recovery plan '{plan_id}' not found")

    plan.approved_by = payload.approved_by
    plan.approval_id = payload.approval_id or f"appr_{plan_id}"
    return plan


@recovery_router.post("/{plan_id}/execute-containment", summary="Execute containment barrier")
@router.post("/recovery/{plan_id}/execute-containment", summary="Execute containment barrier (alias)")
async def execute_containment(plan_id: str, actor: str = Query(default="operator")) -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    return coord.execute_containment(plan_id=plan_id, actor=actor)


@recovery_router.post("/{plan_id}/execute", summary="Execute recovery steps")
@router.post("/recovery/{plan_id}/execute", summary="Execute recovery steps (alias)")
async def execute_recovery(plan_id: str, actor: str = Query(default="operator")) -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    return coord.execute_recovery(plan_id=plan_id, actor=actor)


@recovery_router.post("/{plan_id}/verify", summary="Deterministically verify recovery")
@router.post("/recovery/{plan_id}/verify", summary="Deterministically verify recovery (alias)")
async def verify_recovery(plan_id: str, payload: VerificationPayload) -> dict[str, Any]:
    coord = get_resilience_intelligence_coordinator()
    passed, plan = coord.verify_recovery(plan_id=plan_id, live_telemetry=payload.live_telemetry)
    return {
        "plan_id": plan_id,
        "verified": passed,
        "state": plan.state.value,
        "confidence": plan.confidence,
        "criteria": [c.model_dump() for c in plan.verification_criteria],
    }


@recovery_router.post("/{plan_id}/rollback", response_model=RecoveryPlan, summary="Rollback recovery steps")
@router.post("/recovery/{plan_id}/rollback", response_model=RecoveryPlan, summary="Rollback recovery steps (alias)")
async def rollback_recovery(plan_id: str, actor: str = Query(default="operator")) -> RecoveryPlan:
    coord = get_resilience_intelligence_coordinator()
    return coord.rollback_recovery(plan_id=plan_id, actor=actor)


@recovery_router.post("/{plan_id}/abort", response_model=RecoveryPlan, summary="Abort recovery execution")
@router.post("/recovery/{plan_id}/abort", response_model=RecoveryPlan, summary="Abort recovery execution (alias)")
async def abort_recovery(plan_id: str, payload: AbortPayload, actor: str = Query(default="operator")) -> RecoveryPlan:
    coord = get_resilience_intelligence_coordinator()
    return coord.abort_recovery(plan_id=plan_id, reason=payload.reason, actor=actor)


@recovery_router.post("/{plan_id}/handoff", response_model=HumanHandoffPacket, summary="Escalate recovery to human operator")
@router.post("/recovery/{plan_id}/handoff", response_model=HumanHandoffPacket, summary="Escalate recovery to human operator (alias)")
async def handoff_recovery(plan_id: str, payload: HandoffPayload) -> HumanHandoffPacket:
    coord = get_resilience_intelligence_coordinator()
    return coord.escalate_human_handoff(plan_id=plan_id, incident_id=payload.incident_id, reason=payload.reason)

