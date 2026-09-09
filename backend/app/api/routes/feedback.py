"""User Feedback REST API endpoints for Kairo.

Supports:
- POST /api/v1/feedback (positive, negative, correction, rating, comment)
- GET /api/v1/feedback (list own user feedback with tenant isolation)
- GET /api/v1/feedback/{id} (get own user feedback)
"""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.experience.models import UserFeedbackRecord
from app.experience.schemas import (
    CreateFeedbackRequest,
    FeedbackType,
    UserFeedback,
)
from app.experience.service import ExperienceService

logger = logging.getLogger("kairo.api.feedback")

router = APIRouter(prefix="/feedback", tags=["User Feedback"])


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_experience_service() -> ExperienceService:
    """Dependency provider for ExperienceService."""
    return ExperienceService()


@router.post(
    "",
    response_model=UserFeedback,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback on assistant response or action",
    description="Records positive/negative feedback, ratings, comments, and explicit corrections.",
)
async def submit_feedback(
    payload: CreateFeedbackRequest,
    user_id: str = Depends(get_current_user_id),
    service: ExperienceService = Depends(get_experience_service),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> UserFeedback:
    """Submit feedback. Enforces user ownership and safe sanitization."""
    try:
        feedback = await service.record_feedback(
            user_id=user_id,
            feedback_type=payload.feedback_type,
            session_id=payload.session_id,
            message_id=payload.message_id,
            rating=payload.rating,
            comment=payload.comment,
            correction=payload.correction,
            db_session=db,
        )
        return feedback
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error("Failed to record feedback for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback.",
        )


@router.get(
    "",
    response_model=List[UserFeedback],
    summary="List feedback submitted by the authenticated user",
    description="Tenant isolated query for the user's past feedback.",
)
async def list_user_feedback(
    user_id: str = Depends(get_current_user_id),
    feedback_type: Optional[FeedbackType] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> List[UserFeedback]:
    """Retrieve list of feedback submitted by the calling user."""
    if db is None:
        return []

    query = (
        select(UserFeedbackRecord)
        .where(UserFeedbackRecord.user_id == user_id)
        .order_by(desc(UserFeedbackRecord.created_at))
    )

    if feedback_type:
        query = query.where(UserFeedbackRecord.feedback_type == feedback_type.value)

    query = query.offset(offset).limit(limit)
    res = await db.execute(query)
    records = res.scalars().all()

    return [
        UserFeedback(
            id=r.id,
            user_id=r.user_id,
            session_id=r.session_id,
            message_id=r.message_id,
            feedback_type=FeedbackType(r.feedback_type),
            rating=r.rating,
            comment=r.comment,
            correction=r.correction,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get(
    "/{feedback_id}",
    response_model=UserFeedback,
    summary="Get single feedback record",
    description="Retrieve a feedback record ensuring strict user ownership.",
)
async def get_feedback_detail(
    feedback_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Optional[AsyncSession] = Depends(get_db_session),
) -> UserFeedback:
    """Retrieve single feedback record with strict user isolation (Section 34)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    stmt = select(UserFeedbackRecord).where(UserFeedbackRecord.id == feedback_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    # Enforce ownership: User A cannot view User B feedback
    if record.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this feedback record.",
        )

    return UserFeedback(
        id=record.id,
        user_id=record.user_id,
        session_id=record.session_id,
        message_id=record.message_id,
        feedback_type=FeedbackType(record.feedback_type),
        rating=record.rating,
        comment=record.comment,
        correction=record.correction,
        created_at=record.created_at,
    )
