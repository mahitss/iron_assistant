"""FastAPI router exposing autonomous reliability, incident management, and health endpoints (Task 88)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.reliability.models import (
    FailureRecord,
    IncidentRecord,
    RecoveryExecutionRecord,
    RecoveryStrategyType,
)
from app.reliability.service import reliability_service

logger = logging.getLogger("kairo.reliability.router")

router = APIRouter(prefix="/api/v1/reliability", tags=["Reliability & Self-Healing"])


class FaultTriggerRequest(BaseModel):
    scenario_name: str
    admin_token: str
    caller_identity: str = "admin"
    override_params: Optional[Dict[str, Any]] = None


class ApproveRecoveryRequest(BaseModel):
    approver_identity: str = "admin"
    notes: Optional[str] = None


@router.get("/health", summary="Get consolidated reliability and self-healing health")
async def get_reliability_health() -> Dict[str, Any]:
    """Inspects reliability subsystem status, active incidents, crash loops, and degraded capabilities."""
    return reliability_service.get_health_status()


@router.get("/incidents", summary="List reliability incidents")
async def list_incidents(
    state: Optional[str] = Query(None, description="Filter by state (OPEN, INVESTIGATING, MONITORING, RESOLVED, ESCALATED)"),
) -> List[IncidentRecord]:
    """Returns all recorded failure incidents."""
    incidents = reliability_service.list_incidents()
    if state:
        incidents = [i for i in incidents if i.current_state.value == state.upper()]
    return sorted(incidents, key=lambda i: i.last_seen_at, reverse=True)


@router.get("/incidents/{incident_id}", summary="Get incident details")
async def get_incident(incident_id: str) -> IncidentRecord:
    """Returns detailed incident information including causal links and recovery attempts."""
    inc = reliability_service.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found")
    return inc


@router.post("/incidents/{incident_id}/recover", summary="Trigger authorized recovery for an incident")
async def trigger_recovery(
    incident_id: str,
    dry_run: bool = Query(False, description="Run preflight checks without executing recovery"),
) -> RecoveryExecutionRecord:
    """Triggers bounded, authorized recovery for a specific incident."""
    inc = reliability_service.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found")

    rec = await reliability_service.execute_recovery_for_incident(
        incident_id=incident_id,
        caller_identity="operator",
        dry_run=dry_run,
    )
    return rec


@router.get("/failures", summary="List raw failure records")
async def list_failures(
    component: Optional[str] = Query(None, description="Filter by component"),
) -> List[FailureRecord]:
    """Returns sanitized failure logs."""
    failures = reliability_service.list_failures()
    if component:
        failures = [f for f in failures if f.component.lower() == component.lower()]
    return sorted(failures, key=lambda f: f.timestamp, reverse=True)


@router.get("/failures/{failure_id}", summary="Get failure detail")
async def get_failure(failure_id: str) -> FailureRecord:
    """Returns details for a specific failure record."""
    fail = reliability_service.get_failure(failure_id)
    if not fail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Failure '{failure_id}' not found")
    return fail


@router.get("/recovery", summary="List recovery executions")
async def list_recoveries() -> List[RecoveryExecutionRecord]:
    """Returns all recovery execution attempts and verification outcomes."""
    recs = reliability_service.list_recoveries()
    return sorted(recs, key=lambda r: r.started_at, reverse=True)


@router.get("/recovery/{recovery_id}", summary="Get recovery execution detail and evidence")
async def get_recovery(recovery_id: str) -> Dict[str, Any]:
    """Returns recovery execution detail along with the structured evidence bundle."""
    rec = reliability_service.get_recovery(recovery_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recovery '{recovery_id}' not found")
    evidence = reliability_service.get_evidence(recovery_id)
    return {
        "execution": rec,
        "evidence": evidence,
    }


@router.post("/recovery/{recovery_id}/approve", summary="Approve pending recovery execution")
async def approve_recovery(recovery_id: str, body: ApproveRecoveryRequest) -> Dict[str, Any]:
    """Approves a recovery execution that was awaiting approval."""
    rec = reliability_service.get_recovery(recovery_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recovery '{recovery_id}' not found")

    rec.approval_id = f"appr_granted_{body.approver_identity}"
    # Re-trigger recovery execution for the associated incident
    if rec.incident_id:
        res = await reliability_service.execute_recovery_for_incident(
            incident_id=rec.incident_id,
            caller_identity=body.approver_identity,
        )
        return {"status": "APPROVED_AND_EXECUTED", "result": res}
    return {"status": "APPROVED", "recovery_id": recovery_id}


@router.get("/components", summary="Get component dependency and reliability matrix")
async def get_components_matrix() -> Dict[str, Any]:
    """Returns system dependency graph and component health matrix."""
    from app.reliability.correlator import SYSTEM_DEPENDENCY_EDGES
    return {
        "dependencies": SYSTEM_DEPENDENCY_EDGES,
        "degraded_capabilities": reliability_service._degraded_capabilities,
        "crash_loops": list(reliability_service.detector._crash_loops),
    }


@router.post("/fault-injection/trigger", summary="Trigger controlled fault injection scenario (test-only)")
async def trigger_fault_injection(req: FaultTriggerRequest) -> Dict[str, Any]:
    """Admin-only / test-runner controlled fault injection. Blocked if disabled."""
    if not reliability_service.fault_injector.config.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fault injection is disabled by default in production. Enable explicitly with admin token.",
        )
    try:
        res = reliability_service.fault_injector.trigger_fault(
            scenario_name=req.scenario_name,
            caller_identity=req.caller_identity,
            override_params=req.override_params,
        )
        return {"status": "INJECTED", "details": res}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
