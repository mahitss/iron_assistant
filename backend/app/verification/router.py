"""FastAPI REST API Router for Kairo Truth, Verification & Self-Correction (Task 42)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.verification.assertions import VerificationContract
from app.verification.claims import Claim, ClaimType, TruthStatus
from app.verification.schemas import (
    CitationValidateRequest,
    CitationValidationResponse,
    ClaimCreateRequest,
    ClaimResponse,
    ConfidenceResponse,
    CorrectionResponse,
    EvidenceCreateRequest,
    EvidenceResponse,
    InvariantViolationResponse,
    SelfCorrectionRequest,
    TriangulateResponse,
    VerificationContractRequest,
    VerificationResultResponse,
    VerificationStatsResponse,
)
from app.verification.service import VerificationService

logger = logging.getLogger("kairo.verification.router")

router = APIRouter(prefix="/verification", tags=["Truth & Verification Engine"])

_service_instance: VerificationService | None = None


def get_verification_service() -> VerificationService:
    """Dependency provider for VerificationService singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = VerificationService()
    return _service_instance


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def _to_claim_response(claim: Claim) -> ClaimResponse:
    return ClaimResponse(
        claim_id=claim.claim_id,
        statement=claim.statement,
        claim_type=claim.claim_type.value,
        subject=claim.subject,
        predicate=claim.predicate,
        object_ref=claim.object_ref,
        source=claim.source,
        scope=claim.scope,
        truth_status=claim.truth_status.value,
        confidence=claim.confidence,
        evidence_refs=claim.evidence_refs,
        created_at=claim.created_at.isoformat(),
        observed_at=claim.observed_at.isoformat(),
        expires_at=claim.expires_at.isoformat() if claim.expires_at else None,
    )


# =============================================================================
# CLAIMS ENDPOINTS
# =============================================================================

@router.post("/claims", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def register_claim(
    req: ClaimCreateRequest,
    service: VerificationService = Depends(get_verification_service),
    user_id: str = Depends(get_current_user_id),
) -> ClaimResponse:
    """Register a new claim with anti-self-attestation and deduplication checks."""
    scope = dict(req.scope)
    scope.setdefault("user_id", user_id)

    claim = service.register_claim(
        statement=req.statement,
        claim_type=req.claim_type,
        subject=req.subject,
        predicate=req.predicate,
        object_ref=req.object_ref,
        source=req.source,
        scope=scope,
        expires_at=req.expires_at,
    )
    return _to_claim_response(claim)


@router.get("/claims", response_model=list[ClaimResponse])
def list_claims(
    status_filter: TruthStatus | None = Query(default=None, alias="status"),
    type_filter: ClaimType | None = Query(default=None, alias="claim_type"),
    subject: str | None = Query(default=None),
    service: VerificationService = Depends(get_verification_service),
) -> list[ClaimResponse]:
    """List claims matching optional status, type, and subject filters."""
    claims = service.list_claims(status=status_filter, claim_type=type_filter, subject=subject)
    return [_to_claim_response(c) for c in claims]


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: str,
    service: VerificationService = Depends(get_verification_service),
) -> ClaimResponse:
    """Retrieve claim details with automated freshness check."""
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Claim '{claim_id}' not found")
    return _to_claim_response(claim)


# =============================================================================
# EVIDENCE ENDPOINTS
# =============================================================================

@router.post("/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def register_evidence(
    req: EvidenceCreateRequest,
    service: VerificationService = Depends(get_verification_service),
    user_id: str = Depends(get_current_user_id),
) -> EvidenceResponse:
    """Register empirical observation with secret redaction and reliability scoring."""
    scope = dict(req.scope)
    scope.setdefault("user_id", user_id)

    evidence = service.register_evidence(
        source_type=req.source_type,
        source_reference=req.source_reference,
        observation=req.observation,
        claim_id=req.claim_id,
        scope=scope,
        checksum=req.checksum,
    )
    return EvidenceResponse(
        evidence_id=evidence.evidence_id,
        source_type=evidence.source_type.value,
        source_reference=evidence.source_reference,
        observation=evidence.observation if isinstance(evidence.observation, dict) else {"val": evidence.observation},
        observed_at=evidence.observed_at.isoformat(),
        reliability=evidence.calculate_reliability(),
        freshness_score=evidence.freshness_score(),
        scope=evidence.scope,
        checksum=evidence.checksum,
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: str,
    service: VerificationService = Depends(get_verification_service),
) -> EvidenceResponse:
    evidence = service.get_evidence(evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found")
    return EvidenceResponse(
        evidence_id=evidence.evidence_id,
        source_type=evidence.source_type.value,
        source_reference=evidence.source_reference,
        observation=evidence.observation if isinstance(evidence.observation, dict) else {"val": evidence.observation},
        observed_at=evidence.observed_at.isoformat(),
        reliability=evidence.calculate_reliability(),
        freshness_score=evidence.freshness_score(),
        scope=evidence.scope,
        checksum=evidence.checksum,
    )


# =============================================================================
# VERIFICATION CONTRACT EXECUTION
# =============================================================================

@router.post("/claims/{claim_id}/verify", response_model=VerificationResultResponse)
def verify_claim(
    claim_id: str,
    req: VerificationContractRequest,
    service: VerificationService = Depends(get_verification_service),
) -> VerificationResultResponse:
    """Execute verification contract against observed data with read-only safety."""
    contract = VerificationContract(
        target=req.target,
        expected_state=req.expected_state,
        verification_steps=req.verification_steps,
        timeout_seconds=req.timeout_seconds,
    )

    try:
        _, result = service.verify_claim_contract(
            claim_id=claim_id,
            contract=contract,
            observed_data=req.observed_data,
            strategy=req.strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return VerificationResultResponse(
        status=result.status.value,
        discrepancies=result.discrepancies,
        confidence=result.confidence,
        verifier=result.verifier,
        evidence_ids=result.evidence_ids,
        duration_ms=round(result.duration_ms, 2),
        checked_at=result.checked_at.isoformat(),
    )


# =============================================================================
# TRIANGULATION & CONFIDENCE
# =============================================================================

@router.get("/claims/{claim_id}/triangulate", response_model=TriangulateResponse)
def triangulate_claim(
    claim_id: str,
    service: VerificationService = Depends(get_verification_service),
) -> TriangulateResponse:
    """Triangulate facts across all linked independent evidence sources."""
    try:
        res = service.triangulate(claim_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return TriangulateResponse(
        claim_id=res.claim_id,
        num_sources=res.num_sources,
        num_independent_sources=res.num_independent_sources,
        agreement_ratio=res.agreement_ratio,
        is_corroborated=res.is_corroborated,
        status=res.status.value,
        discrepancies=res.discrepancies,
        participating_evidence_ids=res.participating_evidence_ids,
        metadata=res.metadata,
    )


@router.get("/claims/{claim_id}/confidence", response_model=ConfidenceResponse)
def evaluate_confidence(
    claim_id: str,
    service: VerificationService = Depends(get_verification_service),
) -> ConfidenceResponse:
    """Compute structured multi-factor confidence and uncertainty report."""
    try:
        report = service.evaluate_confidence(claim_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return ConfidenceResponse(
        level=report.level.value,
        uncertainty_state=report.uncertainty_state.value,
        score=report.score,
        factors=report.factors,
        explanation=report.explanation,
        calibrated_at=report.calibrated_at.isoformat(),
    )


# =============================================================================
# CONTRADICTIONS & SELF-CORRECTION
# =============================================================================

@router.get("/claims/{claim_id}/contradictions")
def check_contradictions(
    claim_id: str,
    service: VerificationService = Depends(get_verification_service),
) -> list[dict[str, Any]]:
    """Check for contradictions against active claims and observations."""
    conflicts = service.check_contradictions(claim_id)
    return [c.to_dict() for c in conflicts]


@router.post("/corrections", response_model=CorrectionResponse, status_code=status.HTTP_201_CREATED)
def self_correct(
    req: SelfCorrectionRequest,
    service: VerificationService = Depends(get_verification_service),
) -> CorrectionResponse:
    """Execute self-correction with oscillation protection and user-facing admission."""
    try:
        corr = service.execute_self_correction(
            original_claim_id=req.original_claim_id,
            corrected_statement=req.corrected_statement,
            supporting_evidence_ids=req.supporting_evidence_ids,
            reason=req.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return CorrectionResponse(
        correction_id=corr.correction_id,
        original_claim_id=corr.original_claim_id,
        original_statement=corr.original_statement,
        corrected_statement=corr.corrected_statement,
        evidence_ids=corr.evidence_ids,
        reason=corr.reason,
        user_admission=corr.user_admission,
        timestamp=corr.timestamp.isoformat(),
        status=corr.status,
        metadata=corr.metadata,
    )


# =============================================================================
# CITATION VALIDATION & INVARIANTS
# =============================================================================

@router.post("/citations/validate", response_model=CitationValidationResponse)
def validate_citation(
    req: CitationValidateRequest,
    service: VerificationService = Depends(get_verification_service),
) -> CitationValidationResponse:
    """Validate citation exists and meaningfully corroborates statement."""
    res = service.validate_citation(
        statement=req.statement,
        citation_ref=req.citation_ref,
        excerpt=req.excerpt,
    )
    return CitationValidationResponse(
        citation_ref=res.citation_ref,
        is_valid=res.is_valid,
        exists=res.exists,
        supports_claim=res.supports_claim,
        rejection_reason=res.rejection_reason,
        extracted_quote=res.extracted_quote,
        evaluated_at=res.evaluated_at.isoformat(),
    )


@router.post("/invariants/evaluate", response_model=list[InvariantViolationResponse])
def evaluate_invariants(
    state_dict: dict[str, Any],
    service: VerificationService = Depends(get_verification_service),
) -> list[InvariantViolationResponse]:
    """Evaluate domain invariants against state dictionary."""
    violations = service.invariants.evaluate_all(state_dict)
    return [
        InvariantViolationResponse(
            rule_id=v.rule_id,
            severity=v.severity,
            message=v.message,
            details=v.details,
        )
        for v in violations
    ]


# =============================================================================
# STATS & METRICS
# =============================================================================

@router.get("/stats", response_model=VerificationStatsResponse)
def get_stats(
    service: VerificationService = Depends(get_verification_service),
) -> VerificationStatsResponse:
    """Return metrics, totals, and historical calibration scores."""
    stats = service.get_stats()
    return VerificationStatsResponse(
        metrics=stats["metrics"],
        total_claims=stats["total_claims"],
        total_evidence=stats["total_evidence"],
        total_contracts=stats["total_contracts"],
        total_corrections=stats["total_corrections"],
        calibration=stats["calibration"],
    )
