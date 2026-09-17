"""FastAPI HTTP router for Task 107:
Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.belief.domain import (
    BeliefScope,
    BeliefStatus,
    EvidenceClassification,
    RevisionReason,
)
from app.belief.schemas import (
    BeliefConflictResponse,
    BeliefCreateRequest,
    BeliefDashboardMetrics,
    BeliefDependencyCreateRequest,
    BeliefDependencyResponse,
    BeliefEvidencePack,
    BeliefExplanationResponse,
    BeliefResponse,
    BeliefRevisionRequest,
    BeliefSnapshotCreateRequest,
    BeliefSnapshotResponse,
    BeliefVersionResponse,
    EvidenceIngestRequest,
    EvidenceItemResponse,
)
from app.belief.service import BeliefService

router = APIRouter(tags=["belief-engine"])


def get_belief_service() -> BeliefService:
    return BeliefService.get_instance()


@router.get("/beliefs/dashboard", response_model=BeliefDashboardMetrics)
def get_dashboard(service: BeliefService = Depends(get_belief_service)):
    return service.get_dashboard_metrics()


@router.get("/belief-dashboard", response_model=BeliefDashboardMetrics)
def get_dashboard_alias(service: BeliefService = Depends(get_belief_service)):
    return service.get_dashboard_metrics()


@router.get("/beliefs", response_model=List[BeliefResponse])
def list_beliefs(
    scope: Optional[str] = Query(None),
    status: Optional[BeliefStatus] = Query(None),
    is_stale: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    service: BeliefService = Depends(get_belief_service),
):
    beliefs = service.list_beliefs(scope=scope, status=status, is_stale=is_stale, limit=limit)
    return [BeliefResponse(**b.model_dump()) for b in beliefs]


@router.post("/beliefs", response_model=BeliefResponse, status_code=status.HTTP_201_CREATED)
def create_belief(
    payload: BeliefCreateRequest,
    service: BeliefService = Depends(get_belief_service),
):
    try:
        belief = service.create_belief(
            subject=payload.subject,
            predicate=payload.predicate,
            object_value=payload.object_value,
            scope=payload.scope,
            initial_confidence=payload.initial_confidence,
            evidence_ids=payload.evidence_ids,
            freshness_ttl_seconds=payload.freshness_ttl_seconds,
            provenance=payload.provenance,
        )
        return BeliefResponse(**belief.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/beliefs/{id}", response_model=BeliefResponse)
def get_belief(id: str, service: BeliefService = Depends(get_belief_service)):
    belief = service.get_belief(id)
    if not belief:
        raise HTTPException(status_code=404, detail=f"Belief '{id}' not found.")
    return BeliefResponse(**belief.model_dump())


@router.get("/beliefs/{id}/versions", response_model=List[BeliefVersionResponse])
def get_belief_versions(id: str, service: BeliefService = Depends(get_belief_service)):
    versions = service.get_belief_versions(id)
    return [BeliefVersionResponse(**v.model_dump()) for v in versions]


@router.get("/beliefs/{id}/explain", response_model=BeliefExplanationResponse)
def explain_belief(id: str, service: BeliefService = Depends(get_belief_service)):
    try:
        return service.explain_belief(id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Belief '{id}' not found.")


@router.get("/beliefs/{id}/pack", response_model=BeliefEvidencePack)
def get_belief_evidence_pack(id: str, service: BeliefService = Depends(get_belief_service)):
    try:
        return service.get_evidence_pack(id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Belief '{id}' not found.")


@router.post("/beliefs/{id}/revise", response_model=BeliefResponse)
def revise_belief(
    id: str,
    payload: BeliefRevisionRequest,
    service: BeliefService = Depends(get_belief_service),
):
    try:
        if not payload.evidence_id_trigger:
            raise HTTPException(status_code=400, detail="evidence_id_trigger required for revision.")
        belief, _, _ = service.arbitrate_and_revise(
            belief_id=id,
            evidence_id=payload.evidence_id_trigger,
            reason=payload.reason,
            notes=payload.notes,
        )
        return BeliefResponse(**belief.model_dump())
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/beliefs/{id}/correct")
def record_user_correction(
    id: str,
    statement: str = Query(..., description="User corrective proposition"),
    service: BeliefService = Depends(get_belief_service),
):
    try:
        corr = service.record_user_correction(belief_id=id, correction_statement=statement)
        return {"status": "SUCCESS", "correction_id": corr.correction_id, "belief_id": id}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/beliefs/{id}/conflicts", response_model=List[BeliefConflictResponse])
def get_belief_conflicts(id: str, service: BeliefService = Depends(get_belief_service)):
    conflicts = service.get_conflicts(id)
    return [BeliefConflictResponse(**c.model_dump()) for c in conflicts]


@router.get("/beliefs/{id}/dependencies", response_model=List[BeliefDependencyResponse])
def get_belief_dependencies(id: str, service: BeliefService = Depends(get_belief_service)):
    deps = service.get_dependencies(id)
    return [BeliefDependencyResponse(**d.model_dump()) for d in deps]


@router.post("/beliefs/dependencies", response_model=BeliefDependencyResponse)
def register_dependency(
    payload: BeliefDependencyCreateRequest,
    service: BeliefService = Depends(get_belief_service),
):
    try:
        dep = service.register_dependency(
            parent_belief_id=payload.parent_belief_id,
            child_belief_id=payload.child_belief_id,
            dependency_strength=payload.dependency_strength,
            is_hard_prerequisite=payload.is_hard_prerequisite,
            notes=payload.notes,
        )
        return BeliefDependencyResponse(**dep.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/beliefs/snapshots", response_model=BeliefSnapshotResponse)
def capture_snapshot(
    payload: BeliefSnapshotCreateRequest,
    service: BeliefService = Depends(get_belief_service),
):
    snap = service.capture_snapshot(
        trigger_type=payload.trigger_type,
        reference_id=payload.reference_id,
        scope=payload.scope,
    )
    return BeliefSnapshotResponse(**snap.model_dump())


@router.get("/beliefs/snapshots/{id}", response_model=BeliefSnapshotResponse)
def get_snapshot(id: str, service: BeliefService = Depends(get_belief_service)):
    snap = service.get_snapshot(id)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Snapshot '{id}' not found.")
    return BeliefSnapshotResponse(**snap.model_dump())


# Evidence endpoints
@router.post("/evidence", response_model=EvidenceItemResponse, status_code=status.HTTP_201_CREATED)
def ingest_evidence(
    payload: EvidenceIngestRequest,
    service: BeliefService = Depends(get_belief_service),
):
    try:
        item = service.ingest_evidence(
            source_id=payload.source_id,
            source_type=payload.source_type,
            scope=payload.scope,
            content=payload.content,
            summary=payload.summary,
            freshness_ttl_seconds=payload.freshness_ttl_seconds,
            derived_from_evidence_ids=payload.derived_from_evidence_ids,
            reliability_weight=payload.reliability_weight,
        )
        return EvidenceItemResponse(**item.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/evidence", response_model=List[EvidenceItemResponse])
def list_evidence(
    limit: int = Query(100, ge=1, le=500),
    service: BeliefService = Depends(get_belief_service),
):
    items = service.list_evidence(limit=limit)
    return [EvidenceItemResponse(**e.model_dump()) for e in items]


@router.get("/evidence/{id}", response_model=EvidenceItemResponse)
def get_evidence(id: str, service: BeliefService = Depends(get_belief_service)):
    item = service.get_evidence(id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Evidence '{id}' not found.")
    return EvidenceItemResponse(**item.model_dump())


@router.get("/conflicts", response_model=List[BeliefConflictResponse])
def list_all_conflicts(service: BeliefService = Depends(get_belief_service)):
    conflicts = service.get_conflicts()
    return [BeliefConflictResponse(**c.model_dump()) for c in conflicts]


@router.get("/belief-revisions")
def list_revisions(
    belief_id: Optional[str] = Query(None),
    service: BeliefService = Depends(get_belief_service),
):
    revs = service.get_revisions(belief_id)
    return [r.model_dump() for r in revs]
