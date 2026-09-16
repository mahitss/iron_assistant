"""FastAPI router for Task 95 Action Transactions and Execution Governance."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.execution.domain import (
    ActionObservation,
    ActionTransaction,
    PostCondition,
    PreflightCheckResult,
    TargetBinding,
    TargetType,
    TransactionStatus,
)
from app.execution.service import ExecutionGovernanceService, get_execution_governance_service

router = APIRouter(prefix="/api/v1/actions", tags=["Execution Governance"])


class PrepareActionRequest(BaseModel):
    decision_id: str
    capability_id: str
    action_reference: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    target_id: str
    target_type: str = "SERVICE"
    target_uri: str = ""
    user_id: str = "default_user"
    idempotency_key: str | None = None
    stability_window_seconds: float = 0.0
    compensation_action: str | None = None
    timeout_seconds: float = 30.0


class ExecuteActionRequest(BaseModel):
    approval_id: str | None = None


class CancelActionRequest(BaseModel):
    reason: str = "Operator requested cancellation"


class RollbackActionRequest(BaseModel):
    reason: str = "Operator initiated rollback"


@router.post("/prepare", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def prepare_action(
    req: PrepareActionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Prepare an idempotent action transaction bound to an explicit target."""
    service = get_execution_governance_service(db=db)
    target = TargetBinding(
        target_type=TargetType(req.target_type.upper()) if hasattr(TargetType, req.target_type.upper()) else TargetType.SERVICE,
        target_id=req.target_id,
        target_uri=req.target_uri,
    )
    try:
        txn = await service.prepare_transaction(
            decision_id=req.decision_id,
            capability_id=req.capability_id,
            action_reference=req.action_reference,
            parameters=req.parameters,
            target=target,
            user_id=req.user_id,
            idempotency_key=req.idempotency_key,
            stability_window_seconds=req.stability_window_seconds,
            compensation_action=req.compensation_action,
            timeout_seconds=req.timeout_seconds,
        )
        return txn.model_dump(mode="json")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.get("", response_model=list[dict[str, Any]])
async def list_actions(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List recent action transactions."""
    service = get_execution_governance_service(db=db)
    txns = service.list_transactions(limit=limit)
    return [t.model_dump(mode="json") for t in txns]


@router.get("/{id}", response_model=dict[str, Any])
async def get_action(
    id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Inspect full detail of an action transaction."""
    service = get_execution_governance_service(db=db)
    txn = service.get_transaction(id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction '{id}' not found.")
    return txn.model_dump(mode="json")


@router.get("/{id}/preflight", response_model=list[dict[str, Any]])
async def get_action_preflight(
    id: str,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve pre-flight check gate results."""
    service = get_execution_governance_service(db=db)
    txn = service.get_transaction(id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction '{id}' not found.")
    return [p.model_dump(mode="json") for p in txn.preflight_checks]


@router.get("/{id}/observations", response_model=list[dict[str, Any]])
async def get_action_observations(
    id: str,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve empirical observations for transaction."""
    service = get_execution_governance_service(db=db)
    txn = service.get_transaction(id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction '{id}' not found.")
    return [o.model_dump(mode="json") for o in txn.observations]


@router.get("/{id}/verification", response_model=dict[str, Any])
async def get_action_verification(
    id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve post-condition verification results."""
    service = get_execution_governance_service(db=db)
    txn = service.get_transaction(id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction '{id}' not found.")
    return {
        "verification_state": txn.verification_state.value,
        "postconditions": [c.model_dump(mode="json") for c in txn.postconditions],
        "outcome_summary": txn.outcome_summary,
    }


@router.get("/{id}/outcome", response_model=dict[str, Any])
async def get_action_outcome(
    id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve verified outcome of an action transaction."""
    service = get_execution_governance_service(db=db)
    txn = service.get_transaction(id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction '{id}' not found.")
    return {
        "transaction_id": txn.transaction_id,
        "status": txn.status.value,
        "outcome_type": txn.outcome_type.value if txn.outcome_type else None,
        "summary": txn.outcome_summary,
        "deviation_score": txn.deviation_score,
        "regret_score": txn.regret_score,
    }


@router.post("/{id}/preflight", response_model=dict[str, Any])
async def trigger_preflight(
    id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Execute 18-gate pre-flight validation."""
    service = get_execution_governance_service(db=db)
    try:
        passed, txn = await service.run_preflight(id, db_session=db)
        return {"passed": passed, "transaction": txn.model_dump(mode="json")}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/{id}/execute", response_model=dict[str, Any])
async def execute_action(
    id: str,
    req: ExecuteActionRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Execute action through ToolExecutor and verify outcome."""
    service = get_execution_governance_service(db=db)
    approval_id = req.approval_id if req else None
    try:
        txn = await service.execute_transaction(id, approval_id=approval_id, db_session=db)
        return txn.model_dump(mode="json")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/{id}/cancel", response_model=dict[str, Any])
async def cancel_action(
    id: str,
    req: CancelActionRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cancel a transaction."""
    service = get_execution_governance_service(db=db)
    reason = req.reason if req else "Operator cancelled"
    try:
        txn = await service.cancel_transaction(id, reason=reason)
        return txn.model_dump(mode="json")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/{id}/rollback", response_model=dict[str, Any])
async def rollback_action(
    id: str,
    req: RollbackActionRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Execute rollback compensation."""
    service = get_execution_governance_service(db=db)
    reason = req.reason if req else "Operator initiated rollback"
    try:
        txn = await service.rollback_transaction(id, reason=reason)
        return txn.model_dump(mode="json")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/{id}/reconcile", response_model=dict[str, Any])
async def reconcile_action(
    id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Reconcile an UNKNOWN state transaction."""
    service = get_execution_governance_service(db=db)
    try:
        txn = await service.reconcile_transaction(id)
        return txn.model_dump(mode="json")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))
