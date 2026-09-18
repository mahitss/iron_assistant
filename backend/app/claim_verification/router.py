"""FastAPI Router for Task 116:
Autonomous Claim Verification, Source Integrity & Evidence Provenance Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.claim_verification.schemas import (
    CreateVerificationRequest,
    VerificationCaseResponse,
    VerificationResultResponse,
)
from app.claim_verification.service import ClaimVerificationService

router = APIRouter(prefix="/api", tags=["Claim Verification"])


def get_service() -> ClaimVerificationService:
    return ClaimVerificationService.get_instance()


# --- Verification Cases ---

@router.post("/verifications", status_code=status.HTTP_201_CREATED)
async def create_verification(req: CreateVerificationRequest) -> Dict[str, Any]:
    """Initiates an autonomous claim verification case or idempotently returns existing case."""
    svc = get_service()
    case, result = await svc.create_verification(req)
    return {
        "case": case.to_dict(),
        "result": result.to_dict(),
    }


@router.get("/verifications")
async def list_verifications(
    status: Optional[str] = Query(None, description="Filter by case status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """List verification cases with optional status filter and pagination."""
    svc = get_service()
    cases = await svc.list_verifications(status=status, limit=limit, offset=offset)
    return [c.to_dict() for c in cases]


@router.get("/verifications/{case_id}")
async def get_verification(case_id: str) -> Dict[str, Any]:
    """Retrieve details and outcome of a specific verification case."""
    svc = get_service()
    case = await svc.get_verification(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Verification case '{case_id}' not found")
    result = await svc.get_result_for_case(case_id)
    return {
        "case": case.to_dict(),
        "result": result.to_dict() if result else None,
    }


@router.post("/verifications/{case_id}/cancel")
async def cancel_verification(case_id: str) -> Dict[str, Any]:
    """Cancel an ongoing or pending verification case."""
    svc = get_service()
    case = await svc.cancel_verification(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Verification case '{case_id}' not found")
    return {"message": "Verification cancelled", "case": case.to_dict()}


@router.post("/verifications/{case_id}/revalidate")
async def revalidate_verification(case_id: str) -> Dict[str, Any]:
    """Trigger revalidation of a verification case against latest source snapshots."""
    svc = get_service()
    res = await svc.revalidate_verification(case_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Verification case '{case_id}' not found")
    case, result = res
    return {
        "message": "Revalidation completed",
        "case": case.to_dict(),
        "result": result.to_dict(),
    }


@router.get("/verifications/{case_id}/claims")
async def get_verification_claims(case_id: str) -> List[Dict[str, Any]]:
    """Get structured decomposed claims and fragments for a case."""
    svc = get_service()
    claims = await svc.get_claims_for_case(case_id)
    return [c.to_dict() for c in claims]


@router.get("/verifications/{case_id}/evidence")
async def get_verification_evidence(case_id: str) -> List[Dict[str, Any]]:
    """Get all supporting evidence artifacts evaluated in a case."""
    svc = get_service()
    evidence = await svc.get_evidence_for_case(case_id)
    return [e.to_dict() for e in evidence]


@router.get("/verifications/{case_id}/provenance")
async def get_verification_provenance(case_id: str) -> Dict[str, Any]:
    """Get DAG nodes and links representing provenance lineage for a case."""
    svc = get_service()
    return await svc.get_provenance_graph(case_id)


@router.get("/verifications/{case_id}/contradictions")
async def get_verification_contradictions(case_id: str) -> List[Dict[str, Any]]:
    """Get all detected direct, numeric, temporal, or state contradictions for a case."""
    svc = get_service()
    contradictions = await svc.get_contradictions_for_case(case_id)
    return [c.to_dict() for c in contradictions]


@router.get("/verifications/{case_id}/gaps")
async def get_verification_gaps(case_id: str) -> List[Dict[str, Any]]:
    """Get unresolved verification gaps and missing evidence needs."""
    svc = get_service()
    gaps = await svc.get_gaps_for_case(case_id)
    return [g.to_dict() for g in gaps]


@router.get("/verifications/{case_id}/timeline")
async def get_verification_timeline(case_id: str) -> List[Dict[str, Any]]:
    """Get append-only event timeline for verification case."""
    svc = get_service()
    events = await svc.get_timeline_for_case(case_id)
    return [e.to_dict() for e in events]


@router.get("/verifications/{case_id}/explanation")
async def get_verification_explanation(case_id: str) -> Dict[str, Any]:
    """Get complete explanation tree detailing justification, corroboration, and uncertainty."""
    svc = get_service()
    expl = await svc.get_explanation(case_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation for case '{case_id}' not found")
    return expl


# --- Claims, Sources, and Evidence Direct Endpoints ---

@router.get("/claims/{claim_id}/verification-status")
async def get_claim_verification_status(claim_id: str) -> Dict[str, Any]:
    """Check verification status and validity window for a claim."""
    svc = get_service()
    status_info = await svc.get_claim_verification_status(claim_id)
    if not status_info:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in verification registry")
    return status_info


@router.get("/sources/{source_id}")
async def get_source(source_id: str) -> Dict[str, Any]:
    """Get source identity, category, and multi-dimensional trust profile."""
    svc = get_service()
    src = await svc.get_source(source_id)
    if not src:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return src.to_dict()


@router.get("/sources/{source_id}/history")
async def get_source_history(source_id: str) -> List[Dict[str, Any]]:
    """Get point-in-time snapshots and drift history for a source."""
    svc = get_service()
    snaps = await svc.get_source_history(source_id)
    return [s.to_dict() for s in snaps]


@router.get("/sources/{source_id}/relationships")
async def get_source_relationships(source_id: str) -> List[Dict[str, Any]]:
    """Get copy, citation, or common origin relationships for a source."""
    svc = get_service()
    rels = await svc.get_source_relationships(source_id)
    return [r.to_dict() for r in rels]


@router.get("/evidence/{evidence_id}/lineage")
async def get_evidence_lineage(evidence_id: str) -> List[Dict[str, Any]]:
    """Get lineage path tracing back from evidence artifact to origin source."""
    svc = get_service()
    return await svc.get_evidence_lineage(evidence_id)
