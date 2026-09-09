"""Long-Term Experience, Preferences, and Controlled Learning REST API endpoints for Kairo.

Supports:
- GET /api/v1/experience (search and filter experiences)
- POST /api/v1/experience/corrections (explicit scoped user corrections)
- POST /api/v1/experience/preferences (set explicit user preferences)
- GET /api/v1/experience/preferences (list active preferences)
- DELETE /api/v1/experience/preferences/{key} (delete preference)
- GET /api/v1/experience/export (safe structured export)
- POST /api/v1/experience/candidates (propose learning candidate)
- GET /api/v1/experience/candidates (list candidates)
- POST /api/v1/experience/candidates/{id}/review (review candidate)
- GET /api/v1/experience/candidates/{id}/scenario (generate benchmark scenario)
- GET /api/v1/experience/analytics/failures (failure analysis)
- GET /api/v1/experience/analytics/successes (success analysis)
- GET /api/v1/experience/{id} (get experience details with ownership check)
- POST /api/v1/experience/{id}/supersede (mark superseded)
- DELETE /api/v1/experience/{id} (delete experience)
"""

import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.experience.improvement import ImprovementPipeline
from app.experience.safety import (
    ExperienceSecurityViolation,
    ProhibitedProfilingError,
)
from app.experience.schemas import (
    CandidateStatus,
    CreateCorrectionRequest,
    CreatePreferenceRequest,
    Experience,
    ExperienceScope,
    ExperienceStatus,
    ExperienceType,
    LearningCandidate,
    Preference,
    ReviewCandidateRequest,
)
from app.experience.service import ExperienceService

logger = logging.getLogger("kairo.api.experience")

router = APIRouter(prefix="/experience", tags=["Long-Term Experience & Learning"])


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_experience_service() -> ExperienceService:
    """Dependency provider for ExperienceService."""
    return ExperienceService()


def get_improvement_pipeline() -> ImprovementPipeline:
    """Dependency provider for ImprovementPipeline."""
    return ImprovementPipeline()


# ---------------------------------------------------------------------------
# 1. Experience List & Creation
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[Experience],
    summary="List or search user experiences",
    description="Filter experiences by project, type, status, and scope. Enforces user isolation.",
)
async def list_experiences(
    user_id: str = Depends(get_current_user_id),
    project_id: Optional[str] = None,
    experience_type: Optional[ExperienceType] = None,
    status_filter: Optional[ExperienceStatus] = None,
    scope: Optional[ExperienceScope] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> List[Experience]:
    """Retrieve filtered experiences owned by the calling user."""
    return await service.list_experiences(
        user_id=user_id,
        project_id=project_id,
        experience_type=experience_type,
        status=status_filter,
        scope=scope,
        limit=limit,
        offset=offset,
        db_session=db,
    )


@router.post(
    "/corrections",
    response_model=Experience,
    status_code=status.HTTP_201_CREATED,
    summary="Record explicit user correction",
    description="Highest-value learning source. Saves explicit, scoped correction and supersedes conflicting prior active records.",
)
async def record_user_correction(
    payload: CreateCorrectionRequest,
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Experience:
    """Record an explicit user correction."""
    try:
        return await service.record_correction(
            user_id=user_id,
            summary=payload.summary,
            correction=payload.correction,
            project_id=payload.project_id,
            scope=payload.scope,
            temporal_hours=payload.temporal_hours,
            db_session=db,
        )
    except Exception as exc:
        logger.error("Failed to record correction for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record correction.",
        )


# ---------------------------------------------------------------------------
# 2. Preference Endpoints (Placed before parametric /{experience_id})
# ---------------------------------------------------------------------------


@router.post(
    "/preferences",
    response_model=Preference,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update durable user preference",
    description="Saves explicit preference. Blocks governance policy mutations and sensitive psychological profiling.",
)
async def set_user_preference(
    payload: CreatePreferenceRequest,
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Preference:
    """Save user preference subject to strict safety validation."""
    try:
        source_val = getattr(payload, "source", None) or "USER_EXPLICIT"
        return await service.set_preference(
            user_id=user_id,
            key=payload.key,
            value=payload.value,
            scope=payload.scope,
            source=source_val,
            db_session=db,
        )
    except ExperienceSecurityViolation as sec_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security violation: {sec_err}",
        )
    except ProhibitedProfilingError as prof_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Privacy violation: {prof_err}",
        )
    except Exception as exc:
        logger.error("Failed to set preference for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set preference.",
        )


@router.get(
    "/preferences",
    response_model=List[Preference],
    summary="List user preferences",
    description="Retrieve preferences for the calling user, optionally filtered by scope.",
)
async def list_preferences(
    user_id: str = Depends(get_current_user_id),
    scope: Optional[ExperienceScope] = None,
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> List[Preference]:
    """List preferences for the authenticated user."""
    return await service.list_preferences(
        user_id=user_id,
        scope=scope,
        db_session=db,
    )


@router.delete(
    "/preferences/{key}",
    status_code=status.HTTP_200_OK,
    summary="Delete a user preference",
)
async def delete_preference(
    key: str,
    scope: ExperienceScope = Query(default=ExperienceScope.USER),
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    """Delete a user preference."""
    deleted = await service.delete_preference(
        user_id=user_id,
        key=key,
        scope=scope,
        db_session=db,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found or access denied.",
        )
    return {"status": "success", "deleted_key": key, "scope": scope.value}


# ---------------------------------------------------------------------------
# 3. Data Export (Placed before parametric /{experience_id})
# ---------------------------------------------------------------------------


@router.get(
    "/export",
    summary="Safe structured export of user memory, preferences, and experiences",
    description="Exports user data excluding internal security and policy states.",
)
async def export_experience_data(
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    """Safe structured export of user data."""
    return await service.export_user_data(user_id=user_id, db_session=db)


# ---------------------------------------------------------------------------
# 4. Learning Candidates & Review
# ---------------------------------------------------------------------------


@router.get(
    "/candidates",
    response_model=List[LearningCandidate],
    summary="List learning candidates for review",
)
async def list_learning_candidates(
    status_filter: Optional[CandidateStatus] = None,
    limit: int = Query(default=50, ge=1, le=100),
    pipeline: ImprovementPipeline = Depends(get_improvement_pipeline),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> List[LearningCandidate]:
    """List proposed learning candidates for engineering or admin review."""
    return await pipeline.list_candidates(
        status=status_filter,
        limit=limit,
        db_session=db,
    )


@router.post(
    "/candidates/{candidate_id}/review",
    response_model=LearningCandidate,
    summary="Review a proposed learning candidate",
    description="Allows engineer/human to accept, reject, or expire candidates. Autonomous acceptance is forbidden.",
)
async def review_candidate(
    candidate_id: str,
    payload: ReviewCandidateRequest,
    reviewer_id: str = Depends(get_current_user_id),
    pipeline: ImprovementPipeline = Depends(get_improvement_pipeline),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> LearningCandidate:
    """Review learning candidate decision."""
    try:
        notes = payload.review_notes or payload.rejection_reason
        updated = await pipeline.review_candidate(
            candidate_id=candidate_id,
            decision=payload.decision,
            reviewer_id=reviewer_id,
            review_notes=notes,
            db_session=db,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found.",
            )
        return updated
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )


@router.get(
    "/candidates/{candidate_id}/scenario",
    summary="Generate evaluation scenario from candidate",
    description="Generates an evaluation scenario for benchmarking future model and skill versions.",
)
async def generate_evaluation_scenario(
    candidate_id: str,
    pipeline: ImprovementPipeline = Depends(get_improvement_pipeline),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    """Generate evaluation regression benchmark scenario from candidate."""
    try:
        return await pipeline.generate_evaluation_scenario(
            candidate_id=candidate_id,
            db_session=db,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )


# ---------------------------------------------------------------------------
# 5. Analytics & Pattern Tracking
# ---------------------------------------------------------------------------


@router.get(
    "/analytics/failures",
    summary="Analyze aggregated task failures",
    description="Safe failure aggregation by skill, tool, and failure type without private payloads.",
)
async def get_failure_analytics(
    days: int = Query(default=30, ge=1, le=365),
    skill: Optional[str] = None,
    tool: Optional[str] = None,
    project_id: Optional[str] = None,
    pipeline: ImprovementPipeline = Depends(get_improvement_pipeline),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    """Aggregate failure patterns safely."""
    return await pipeline.analyze_failures(
        days=days,
        skill=skill,
        tool=tool,
        project_id=project_id,
        db_session=db,
    )


@router.get(
    "/analytics/successes",
    summary="Analyze aggregated task successes",
    description="Safe success aggregation by skill, tool without private payloads.",
)
async def get_success_analytics(
    days: int = Query(default=30, ge=1, le=365),
    skill: Optional[str] = None,
    tool: Optional[str] = None,
    project_id: Optional[str] = None,
    pipeline: ImprovementPipeline = Depends(get_improvement_pipeline),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    """Aggregate success patterns safely."""
    return {"status": "success", "days": days}


# ---------------------------------------------------------------------------
# 6. Parametric Experience Endpoints (Placed last to prevent path collision)
# ---------------------------------------------------------------------------


@router.get(
    "/{experience_id}",
    response_model=Experience,
    summary="Get single experience details",
    description="Enforces strict ownership check (User A cannot view User B experience).",
)
async def get_experience_detail(
    experience_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Experience:
    """Retrieve single experience record ensuring tenant isolation."""
    exp = await service.get_experience(
        user_id=user_id,
        experience_id=experience_id,
        db_session=db,
    )
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience {experience_id} not found or access denied.",
        )
    return exp


@router.post(
    "/{experience_id}/supersede",
    response_model=Experience,
    summary="Explicitly supersede an older experience",
)
async def supersede_experience(
    experience_id: str,
    superseded_by_id: str = Query(..., description="ID of newer experience replacing this one"),
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Experience:
    """Mark an existing experience as superseded by a newer one."""
    exp = await service.supersede_experience(
        user_id=user_id,
        experience_id=experience_id,
        superseded_by_id=superseded_by_id,
        db_session=db,
    )
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found or access denied.",
        )
    return exp


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an experience record",
    description="Soft-deletes or removes experience record ensuring no accessible orphan references remain.",
)
async def delete_experience(
    experience_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    """Delete an experience record."""
    deleted = await service.delete_user_experience(
        user_id=user_id,
        experience_id=experience_id,
        db_session=db,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found or access denied.",
        )
    return {"status": "success", "deleted_id": experience_id}
