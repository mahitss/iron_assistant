"""Canonical data models, enums, and schemas for Kairo Experience & Learning System."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExperienceType(str, Enum):
    """Categorical type of experience signal."""

    USER_CORRECTION = "USER_CORRECTION"
    TASK_SUCCESS = "TASK_SUCCESS"
    TASK_FAILURE = "TASK_FAILURE"
    USER_PREFERENCE = "USER_PREFERENCE"
    WORKFLOW_OUTCOME = "WORKFLOW_OUTCOME"
    AGENT_OUTCOME = "AGENT_OUTCOME"
    TOOL_OUTCOME = "TOOL_OUTCOME"
    EVALUATION_SIGNAL = "EVALUATION_SIGNAL"
    PROJECT_CHANGE = "PROJECT_CHANGE"


class ExperienceStatus(str, Enum):
    """Lifecycle state of an experience record."""

    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    DELETED = "DELETED"


class ExperienceSource(str, Enum):
    """Originating source of the experience record."""

    USER_EXPLICIT = "USER_EXPLICIT"
    USER_FEEDBACK = "USER_FEEDBACK"
    SYSTEM_OBSERVED = "SYSTEM_OBSERVED"
    EVALUATION = "EVALUATION"
    PROJECT_EVENT = "PROJECT_EVENT"


class ExperienceScope(str, Enum):
    """Granularity and application boundary of an experience or preference."""

    GLOBAL = "GLOBAL"
    USER = "USER"
    PROJECT = "PROJECT"
    CONVERSATION = "CONVERSATION"
    TASK = "TASK"
    DEVICE = "DEVICE"
    SKILL = "SKILL"


class FailureType(str, Enum):
    """Classification of task and tool failures."""

    MODEL_FAILURE = "MODEL_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    AUTH_FAILURE = "AUTH_FAILURE"
    PERMISSION_FAILURE = "PERMISSION_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    USER_CANCELLED = "USER_CANCELLED"
    TIMEOUT = "TIMEOUT"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    """Degree of certainty in experience or preference."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CandidateStatus(str, Enum):
    """Review status of a proposed learning candidate."""

    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class FeedbackType(str, Enum):
    """User feedback categories."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    CORRECTION = "CORRECTION"
    RATING = "RATING"
    COMMENT = "COMMENT"


# --- Core Domain Models ---


class Experience(BaseModel):
    """Canonical representation of an observed or validated task experience."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    project_id: Optional[str] = None
    type: ExperienceType
    source: ExperienceSource
    summary: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: ExperienceStatus = ExperienceStatus.ACTIVE
    scope: ExperienceScope = ExperienceScope.PROJECT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Preference(BaseModel):
    """Durable user or project preference."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    scope: ExperienceScope = ExperienceScope.PROJECT
    key: str
    value: Any
    source: ExperienceSource = ExperienceSource.USER_EXPLICIT
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    status: ExperienceStatus = ExperienceStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LearningCandidate(BaseModel):
    """Proposed systemic improvement awaiting engineering or evaluation review."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_event: str
    proposed_change: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    scope: ExperienceScope = ExperienceScope.GLOBAL
    status: CandidateStatus = CandidateStatus.PROPOSED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_by: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class UserFeedback(BaseModel):
    """Raw feedback submitted by an authenticated user on an interaction."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    feedback_type: FeedbackType
    rating: Optional[int] = None
    comment: Optional[str] = None
    correction: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# --- Request / Response DTOs ---


class CreateFeedbackRequest(BaseModel):
    """Schema for submitting user feedback."""

    session_id: Optional[str] = None
    message_id: Optional[str] = None
    feedback_type: FeedbackType = FeedbackType.POSITIVE
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None
    correction: Optional[str] = None


class CreateCorrectionRequest(BaseModel):
    """Schema for submitting an explicit user correction."""

    project_id: Optional[str] = None
    summary: str = Field(..., min_length=2, description="Concise summary of the correction")
    correction: str = Field(..., min_length=2, description="The corrected factual statement")
    scope: ExperienceScope = ExperienceScope.PROJECT
    temporal_hours: Optional[int] = Field(default=None, description="Optional hours until expiration for temporary corrections")


class CreatePreferenceRequest(BaseModel):
    """Schema for setting a user or project preference."""

    key: str = Field(..., min_length=1)
    value: Any
    scope: ExperienceScope = ExperienceScope.PROJECT
    source: ExperienceSource = ExperienceSource.USER_EXPLICIT


class ReviewCandidateRequest(BaseModel):
    """Schema for reviewing a proposed learning candidate."""

    decision: CandidateStatus = Field(..., description="ACCEPTED or REJECTED")
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
