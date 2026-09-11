"""FastAPI REST API endpoints for Kairo Metacognitive Control & Self-Audit Engine (Task 67)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.self_audit.schemas import (
    AuditCycleRequest,
    BeliefCreateRequest,
    BeliefReviseRequest,
    SelfAuditCreateRequest,
)
from app.self_audit.service import SelfAuditService, self_audit_service

router = APIRouter(prefix="/self-audit", tags=["self-audit"])


def get_self_audit_service(db: Session = Depends(get_db)) -> SelfAuditService:
    if db is not None:
        self_audit_service.db = db
    return self_audit_service


@router.get("/health", response_model=dict[str, Any])
def get_self_audit_health(
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Health check endpoint for Metacognitive Control & Autonomous Self-Audit Engine."""
    model = service.self_model_mgr.get_or_create_self_model()
    return {
        "status": "ok",
        "engine": "Kairo Metacognitive Control & Self-Audit Engine",
        "task": 67,
        "metacognitive_state": model.current_state.value,
        "calibration_state": model.calibration.value,
        "capabilities_tracked": len(model.capabilities),
    }


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_self_audit(
    request: SelfAuditCreateRequest,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Trigger an operational self-audit on a specific subject (Spec 45, 64)."""
    try:
        effective_tenant = tenant_id if tenant_id != "default" else request.tenant_id
        record = service.create_audit(request, tenant_id=effective_tenant)
        return record.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/cycle", response_model=dict[str, Any])
def run_audit_cycle(
    request: AuditCycleRequest,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Execute full 11-step metacognitive audit cycle with optional adversarial review (Spec 2, 22, 93)."""
    try:
        effective_tenant = tenant_id if tenant_id != "default" else request.tenant_id
        record = service.run_cycle(
            subject=request.subject,
            observed_actions=request.observed_actions,
            reported_confidence=request.reported_confidence,
            observed_outcomes=request.observed_outcomes,
            depth=request.depth,
            is_adversarial=request.is_adversarial,
            tenant_id=effective_tenant,
        )
        return record.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/", response_model=list[dict[str, Any]])
def list_self_audits(
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> list[dict[str, Any]]:
    """List all executed self-audits for tenant."""
    audits = service.list_audits(tenant_id=tenant_id)
    return [a.model_dump() for a in audits]


@router.get("/overview", response_model=dict[str, Any])
def get_self_audit_overview(
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Retrieve Self-Audit Control Center dashboard telemetry (Spec 59)."""
    overview = service.get_overview(tenant_id=tenant_id)
    return overview.model_dump()


@router.get("/history", response_model=list[dict[str, Any]])
def get_audit_history(
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> list[dict[str, Any]]:
    """Retrieve chronological audit run history."""
    return service.get_history(tenant_id=tenant_id)


@router.get("/drift", response_model=list[dict[str, Any]])
def get_behavior_drift(
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> list[dict[str, Any]]:
    """Retrieve operational behavior drift indicators and threshold alerts (Spec 34, 64)."""
    return service.get_drift(tenant_id=tenant_id)


@router.get("/calibration", response_model=dict[str, Any])
def get_confidence_calibration(
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Retrieve confidence calibration metrics and aggregate Brier scores (Spec 24, 64)."""
    return service.get_calibration(tenant_id=tenant_id)


@router.get("/errors", response_model=dict[str, Any])
def get_error_taxonomy_and_clusters(
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Retrieve 12-category error taxonomy distribution and recurring failure clusters (Spec 27, 29, 64)."""
    return service.get_errors(tenant_id=tenant_id)


@router.get("/beliefs", response_model=list[dict[str, Any]])
def list_beliefs(
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> list[dict[str, Any]]:
    """List internal active and questioned system beliefs (Spec 7)."""
    beliefs = service.list_beliefs(tenant_id=tenant_id)
    return [b.model_dump() for b in beliefs]


@router.post("/beliefs", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def register_belief(
    request: BeliefCreateRequest,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Register an internal system belief with basis and evidence (Spec 7)."""
    try:
        effective_tenant = tenant_id if tenant_id != "default" else request.tenant_id
        belief = service.register_belief(request, tenant_id=effective_tenant)
        return belief.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/beliefs/{belief_id}/revise", response_model=dict[str, Any])
def revise_belief(
    belief_id: str,
    request: BeliefReviseRequest,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Revise an existing belief non-destructively preserving audit lineage (Spec 8)."""
    try:
        effective_tenant = tenant_id if tenant_id != "default" else request.tenant_id
        revised = service.revise_belief(belief_id, request, tenant_id=effective_tenant)
        return revised.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Belief '{belief_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{audit_id}", response_model=dict[str, Any])
def get_self_audit(
    audit_id: str,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Retrieve detailed self-audit record by id."""
    try:
        audit = service.get_audit(audit_id, tenant_id=tenant_id)
        return audit.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Self-audit '{audit_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{audit_id}/findings", response_model=list[dict[str, Any]])
def get_audit_findings(
    audit_id: str,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> list[dict[str, Any]]:
    """Retrieve structured findings discovered during self-audit (Spec 50, 64)."""
    try:
        findings = service.get_findings(audit_id, tenant_id=tenant_id)
        return [f.model_dump() for f in findings]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Self-audit '{audit_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{audit_id}/evidence", response_model=list[str])
def get_audit_evidence(
    audit_id: str,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> list[str]:
    """Retrieve empirical evidence citations collected during self-audit (Spec 64)."""
    try:
        return service.get_evidence(audit_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Self-audit '{audit_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{audit_id}/reassess", response_model=dict[str, Any])
def reassess_audit(
    audit_id: str,
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Re-evaluate an existing audit against current state (Spec 47, 64)."""
    try:
        reassessed = service.reassess_audit(audit_id, tenant_id=tenant_id)
        return reassessed.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Self-audit '{audit_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/findings/{finding_id}/resolve", response_model=dict[str, Any])
def resolve_audit_finding(
    finding_id: str,
    evidence: str = Query(..., description="Empirical evidence verifying problem resolution"),
    tenant_id: str = Query(default="default"),
    service: SelfAuditService = Depends(get_self_audit_service),
) -> dict[str, Any]:
    """Empirically resolve an audit finding (Spec 81, 82)."""
    try:
        resolved = service.resolve_finding(finding_id, resolution_evidence=evidence, tenant_id=tenant_id)
        return resolved.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding '{finding_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
