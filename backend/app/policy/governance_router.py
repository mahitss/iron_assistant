"""FastAPI REST API router for Kairo Autonomous Governance, Constitutional Reasoning,
and Authority Management Engine (Task 78).
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status

from app.policy.governance_coordinator import (
    GovernanceIntelligenceCoordinator,
    default_governance_coordinator,
)
from app.policy.governance_schemas import (
    AuthorityGrant,
    AuthorityLevel,
    ConstitutionModelSchema,
    GovernanceDashboardSummary,
    GovernanceDecisionResult,
    GovernanceReviewRequest,
    PrincipleName,
    PrincipleStrictness,
)
from app.policy.router import require_policy_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["governance"])


def get_governance_coordinator() -> GovernanceIntelligenceCoordinator:
    """Dependency provider for GovernanceIntelligenceCoordinator."""
    return default_governance_coordinator


# ==============================================================================
# Governance Review & Decision Endpoints
# ==============================================================================

@router.post(
    "/review",
    response_model=GovernanceDecisionResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate an autonomous action for constitutional, authority, and policy compliance",
)
async def evaluate_governance_review(
    request: GovernanceReviewRequest,
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> GovernanceDecisionResult:
    """Submit candidate autonomous action for pre-execution governance review."""
    try:
        return await coordinator.evaluate_review(request)
    except Exception as e:
        logger.error("Error during governance evaluation: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Governance reasoning failure: {str(e)}",
        )


@router.get(
    "/reviews/pending-human",
    response_model=list[GovernanceDecisionResult],
    status_code=status.HTTP_200_OK,
    summary="List all reviews currently awaiting human oversight and judgment",
)
async def list_pending_human_reviews(
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> list[GovernanceDecisionResult]:
    """Retrieve all pending actions blocked awaiting human review."""
    return coordinator.list_pending_human_reviews()


@router.get(
    "/reviews/{review_id}",
    response_model=GovernanceDecisionResult,
    status_code=status.HTTP_200_OK,
    summary="Get governance decision record by review ID",
)
async def get_governance_review(
    review_id: str,
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> GovernanceDecisionResult:
    """Fetch stored decision, constitutional score, evidence, and rationale."""
    res = coordinator.get_decision(review_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Governance review '{review_id}' not found.",
        )
    return res


@router.post(
    "/reviews/{review_id}/resolve",
    response_model=GovernanceDecisionResult,
    status_code=status.HTTP_200_OK,
    summary="Submit verified human review judgment (Approve or Deny)",
)
async def resolve_human_review(
    review_id: str,
    payload: dict[str, Any] = Body(...),
    x_caller_type: Annotated[str | None, Header()] = None,
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> GovernanceDecisionResult:
    """Record human judgment. CRITICAL: AI model or autonomous agent cannot self-approve."""
    caller_type = (x_caller_type or "").lower()
    if caller_type in ("agent", "model", "llm", "autonomous_task", "kairo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autonomous agent or model cannot self-approve human reviews.",
        )

    reviewer_id = payload.get("reviewer_id")
    if not reviewer_id or reviewer_id in ("kairo", "autonomous_agent", "self"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid human reviewer_id is required. Self-approval is strictly prohibited.",
        )

    approved = bool(payload.get("approved", False))
    rationale = str(payload.get("rationale", ""))

    try:
        return coordinator.resolve_human_review(
            review_id=review_id,
            reviewer_id=reviewer_id,
            approved=approved,
            rationale=rationale,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Governance review '{review_id}' not found.",
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ==============================================================================
# Constitution Endpoints
# ==============================================================================

@router.get(
    "/constitution",
    response_model=ConstitutionModelSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current active machine-readable constitution and principles",
)
async def get_constitution(
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> ConstitutionModelSchema:
    """Inspect active constitutional principles, weights, and strictness definitions."""
    return coordinator.constitutional_engine.constitution


@router.put(
    "/constitution/principles/{principle_name}",
    status_code=status.HTTP_200_OK,
    summary="Update constitutional principle weight, strictness, or enabled state (Admin only)",
)
async def update_constitutional_principle(
    principle_name: str,
    payload: dict[str, Any] = Body(...),
    admin_id: str = Depends(require_policy_admin),
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> dict[str, Any]:
    """Admin configuration of constitutional principles."""
    try:
        p_name = PrincipleName(principle_name.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid principle name '{principle_name}'. Valid principles: {[p.value for p in PrincipleName]}",
        )

    weight = payload.get("weight")
    strictness_str = payload.get("strictness")
    strictness = PrincipleStrictness(strictness_str.upper()) if strictness_str else None
    enabled = payload.get("enabled")

    updated = coordinator.constitutional_engine.update_principle(
        name=p_name,
        weight=weight,
        strictness=strictness,
        enabled=enabled,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Principle '{principle_name}' not found.",
        )

    return {
        "status": "success",
        "principle": p_name.value,
        "updated_by": admin_id,
        "principle_details": coordinator.constitutional_engine.get_principle(p_name),
    }


# ==============================================================================
# Authority Management Endpoints
# ==============================================================================

@router.post(
    "/authority/grant",
    response_model=AuthorityGrant,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a discrete authority grant to an agent, user, or workflow",
)
async def issue_authority_grant(
    payload: dict[str, Any] = Body(...),
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> AuthorityGrant:
    """Create explicit authority grant separating permission from capability."""
    subject_id = payload.get("subject_id")
    if not subject_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subject_id is required.")

    level_str = payload.get("authority_level", "LIMITED").upper()
    try:
        authority_level = AuthorityLevel(level_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid authority_level '{level_str}'. Valid: {[a.value for a in AuthorityLevel]}",
        )

    grant = coordinator.authority_manager.issue_grant(
        subject_id=subject_id,
        authority_level=authority_level,
        subject_type=payload.get("subject_type", "AGENT"),
        allowed_scopes=payload.get("allowed_scopes", ["*"]),
        allowed_actions=payload.get("allowed_actions", ["*"]),
        denied_actions=payload.get("denied_actions", []),
        max_risk_level=payload.get("max_risk_level", "R2_MODERATE"),
        granted_by=payload.get("granted_by", "api_operator"),
    )
    return grant


@router.get(
    "/authority/{subject_id}",
    status_code=status.HTTP_200_OK,
    summary="Get active authority level and grants for a subject",
)
async def get_subject_authority(
    subject_id: str,
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> dict[str, Any]:
    """Inspect active authority boundaries and grants for specified actor."""
    grants = coordinator.authority_manager.get_active_grants(subject_id)
    highest = coordinator.authority_manager.get_highest_authority(subject_id)
    return {
        "subject_id": subject_id,
        "highest_authority_level": highest.value,
        "highest_authority_rank": highest.rank,
        "active_grants_count": len(grants),
        "grants": grants,
    }


@router.delete(
    "/authority/{subject_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke all active authority grants for a subject",
)
async def revoke_subject_authority(
    subject_id: str,
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> dict[str, Any]:
    """Deactivate all authority grants for specified subject."""
    count = coordinator.authority_manager.revoke_grants(subject_id)
    return {"subject_id": subject_id, "revoked_grants_count": count}


# ==============================================================================
# Dashboard & Security Metrics Endpoints
# ==============================================================================

@router.get(
    "/dashboard",
    response_model=GovernanceDashboardSummary,
    status_code=status.HTTP_200_OK,
    summary="Retrieve consolidated governance intelligence metrics for Command Center",
)
async def get_governance_dashboard_summary(
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> GovernanceDashboardSummary:
    """Return dashboard summary: active policies by tier, pending reviews, and compliance score."""
    return coordinator.get_dashboard_summary()


@router.get(
    "/escalations",
    status_code=status.HTTP_200_OK,
    summary="Get recent authority escalation and control-weakening incidents",
)
async def get_recent_escalations(
    limit: int = Query(default=20, ge=1, le=100),
    coordinator: GovernanceIntelligenceCoordinator = Depends(get_governance_coordinator),
) -> list[dict[str, Any]]:
    """Retrieve flagged privilege bypass and probe hammering attempts."""
    incidents = coordinator.escalation_detector.get_recent_incidents(limit=limit)
    return [i.model_dump() for i in incidents]
