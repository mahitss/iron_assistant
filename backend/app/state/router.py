"""REST API endpoints for Kairo Unified State Fabric (Task 39, Spec 147-154)."""

from datetime import UTC, datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.state.changelog import state_changelog
from app.state.fabric import state_fabric
from app.state.quarantine import state_quarantine
from app.state.reconciliation import state_reconciler
from app.state.schemas import (
    ChangelogEntry,
    ReadConsistency,
    ReconciliationMode,
    ReconciliationReport,
    StateDomain,
    StateRecord,
)
from app.state.snapshots import snapshot_manager

router = APIRouter(prefix="/api/v1/state", tags=["state-fabric"])


@router.get("/health", summary="Get State Fabric Health and Metrics")
async def get_state_health() -> dict[str, Any]:
    """Returns state fabric operational status, record count, and quarantine count."""
    records = state_fabric.get_all_records()
    quarantined = state_quarantine.list_active()
    last_report = state_reconciler.get_last_report()

    return {
        "status": "HEALTHY" if len(quarantined) == 0 else "DEGRADED",
        "active_records_count": len(records),
        "quarantined_count": len(quarantined),
        "last_reconciliation": last_report.model_dump() if last_report else None,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/records/{domain}/{resource_type}/{resource_id}", response_model=StateRecord)
async def get_state_record(
    domain: StateDomain,
    resource_type: str,
    resource_id: str,
    consistency: ReadConsistency = Query(default=ReadConsistency.STRONG),
    user_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> StateRecord:
    """Fetches a state record respecting domain boundary and security scope."""
    record = await state_fabric.get_record(
        domain=domain,
        resource_type=resource_type,
        resource_id=resource_id,
        consistency=consistency,
        request_user_id=user_id,
        request_project_id=project_id,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State record '{domain.value}:{resource_type}:{resource_id}' not found",
        )
    return record


@router.get("/changelog", response_model=list[ChangelogEntry])
async def get_changelog(
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ChangelogEntry]:
    """Queries durable change log entries."""
    return state_changelog.get_history(resource_type=resource_type, resource_id=resource_id, limit=limit)


@router.post("/reconcile", response_model=ReconciliationReport)
async def trigger_reconciliation(
    mode: ReconciliationMode = Query(default=ReconciliationMode.CHECK),
) -> ReconciliationReport:
    """Runs a state reconciliation pass."""
    records = state_fabric.get_all_records()
    return await state_reconciler.reconcile(mode=mode, authoritative_records=records)


@router.get("/reconcile/last", response_model=ReconciliationReport | None)
async def get_last_reconciliation_report() -> ReconciliationReport | None:
    """Returns the most recent reconciliation report."""
    return state_reconciler.get_last_report()


@router.get("/quarantine", summary="List Quarantined State Items")
async def list_quarantine() -> list[dict[str, Any]]:
    """Returns all currently quarantined state records and projections."""
    return [item.to_dict() for item in state_quarantine.list_active()]


@router.post("/quarantine/{resource_id}/release", summary="Release Item from Quarantine")
async def release_from_quarantine(
    resource_id: str,
    operator: str = Query(default="operator"),
) -> dict[str, Any]:
    """Releases a record from quarantine."""
    released = state_quarantine.release(resource_id=resource_id, released_by=operator)
    if not released:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource_id}' is not currently quarantined",
        )
    return {"status": "RELEASED", "resource_id": resource_id, "released_by": operator}
