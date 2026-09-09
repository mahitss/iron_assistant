"""Kairo Long-Term Memory, Experience Learning, Feedback Loop, and Controlled Improvement."""

from app.experience.events_integration import (
    publish_experience_event,
    publish_feedback_event,
    register_experience_subscribers,
)
from app.experience.improvement import ImprovementPipeline
from app.experience.models import (
    ExperienceRecord,
    LearningCandidateRecord,
    PreferenceRecord,
    UserFeedbackRecord,
)
from app.experience.retrieval import ExperienceRetriever
from app.experience.safety import (
    ExperienceSecurityViolation,
    ProhibitedProfilingError,
    sanitize_content,
    validate_learning_candidate,
    validate_preference_safety,
)
from app.experience.schemas import (
    CandidateStatus,
    ConfidenceLevel,
    CreateCorrectionRequest,
    CreateFeedbackRequest,
    CreatePreferenceRequest,
    Experience,
    ExperienceScope,
    ExperienceSource,
    ExperienceStatus,
    ExperienceType,
    FailureType,
    FeedbackType,
    LearningCandidate,
    Preference,
    ReviewCandidateRequest,
    UserFeedback,
)
from app.experience.service import ExperienceService

__all__ = [
    # Schemas
    "ExperienceType",
    "ExperienceStatus",
    "ExperienceSource",
    "ExperienceScope",
    "FailureType",
    "ConfidenceLevel",
    "CandidateStatus",
    "FeedbackType",
    "Experience",
    "Preference",
    "LearningCandidate",
    "UserFeedback",
    "CreateFeedbackRequest",
    "CreateCorrectionRequest",
    "CreatePreferenceRequest",
    "ReviewCandidateRequest",
    # Models
    "ExperienceRecord",
    "PreferenceRecord",
    "LearningCandidateRecord",
    "UserFeedbackRecord",
    # Safety
    "ExperienceSecurityViolation",
    "ProhibitedProfilingError",
    "validate_preference_safety",
    "validate_learning_candidate",
    "sanitize_content",
    # Core Services
    "ExperienceService",
    "ExperienceRetriever",
    "ImprovementPipeline",
    # Events
    "publish_experience_event",
    "publish_feedback_event",
    "register_experience_subscribers",
]
