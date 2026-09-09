"""Kairo Social & Communication Intelligence Engine (Task 49)."""

from app.communication.channels import (
    ChannelAuthorizationError,
    ChannelManager,
    QuietHoursViolationError,
    RateLimitExceededError,
)
from app.communication.classifier import MessageClassifier
from app.communication.commitments import (
    CommitmentFabricationError,
    CommitmentTracker,
)
from app.communication.contacts import (
    ContactAmbiguityError,
    ContactBook,
    ContactNotFoundError,
)
from app.communication.context import (
    CommunicationContextManager,
    ContextIsolationViolationError,
)
from app.communication.delivery import (
    BlindResendError,
    BulkCommunicationAuthorizationError,
    DeliveryManager,
    DuplicateSendError,
)
from app.communication.drafts import (
    DraftEngine,
    DraftHallucinationError,
)
from app.communication.evaluation import CommunicationEvaluator
from app.communication.followups import (
    FollowUpEngine,
    FollowUpLimitExceededError,
)
from app.communication.intent import CommunicationIntentEngine
from app.communication.messages import MessageNormalizer
from app.communication.participants import ParticipantResolver
from app.communication.policies import (
    CommunicationPolicyEngine,
    PolicyGatingError,
)
from app.communication.privacy import (
    PrivacyManager,
    SecretLeakDetectedError,
)
from app.communication.provenance import (
    ImmutableHistoryViolationError,
    ProvenanceTracker,
)
from app.communication.redaction import CommunicationRedactor
from app.communication.relationships import (
    RelationshipEngine,
    SocialProfilingViolationError,
)
from app.communication.responses import ResponseNeedEvaluator
from app.communication.router import router as communication_router
from app.communication.safety import (
    CommunicationSafetyError,
    CommunicationSafetyGuard,
    PromptInjectionDetectedError,
)
from app.communication.schemas import (
    AttachmentSchema,
    CommitmentSchema,
    CommitmentStatus,
    CommunicationChannel,
    CommunicationTone,
    CommunicationUrgency,
    DeliveryReceiptSchema,
    DraftMessageSchema,
    DraftStatus,
    FollowUpSchema,
    FollowUpTrigger,
    MessageCategory,
    MessageDirection,
    MessageSchema,
    MessageStatus,
    ParticipantSchema,
    PrivacyScope,
    RecipientSchema,
    RecipientType,
    RelationshipContextSchema,
    RelationshipType,
    ResponseNeed,
    RiskCategory,
    RiskSeverity,
    SendRequestSchema,
    SummaryResultSchema,
    ThreadSchema,
    ThreadState,
)
from app.communication.sentiment import (
    PsychologicalDiagnosisViolationError,
    SentimentAnalyzer,
)
from app.communication.service import CommunicationService
from app.communication.threads import ThreadEngine
from app.communication.urgency import UrgencyEvaluator
from app.communication.verification import (
    AttachmentVerificationError,
    CommunicationVerifier,
    RecipientLeakError,
)

__all__ = [
    "CommunicationService",
    "communication_router",
    "ChannelManager",
    "ChannelAuthorizationError",
    "RateLimitExceededError",
    "QuietHoursViolationError",
    "MessageNormalizer",
    "ThreadEngine",
    "ParticipantResolver",
    "ContactBook",
    "ContactAmbiguityError",
    "ContactNotFoundError",
    "RelationshipEngine",
    "SocialProfilingViolationError",
    "CommunicationContextManager",
    "ContextIsolationViolationError",
    "MessageClassifier",
    "CommunicationIntentEngine",
    "SentimentAnalyzer",
    "PsychologicalDiagnosisViolationError",
    "UrgencyEvaluator",
    "CommitmentTracker",
    "CommitmentFabricationError",
    "FollowUpEngine",
    "FollowUpLimitExceededError",
    "ResponseNeedEvaluator",
    "DraftEngine",
    "DraftHallucinationError",
    "DeliveryManager",
    "DuplicateSendError",
    "BlindResendError",
    "BulkCommunicationAuthorizationError",
    "CommunicationVerifier",
    "AttachmentVerificationError",
    "RecipientLeakError",
    "PrivacyManager",
    "SecretLeakDetectedError",
    "CommunicationRedactor",
    "CommunicationPolicyEngine",
    "PolicyGatingError",
    "ProvenanceTracker",
    "ImmutableHistoryViolationError",
    "CommunicationSafetyGuard",
    "CommunicationSafetyError",
    "PromptInjectionDetectedError",
    "CommunicationEvaluator",
    "CommunicationChannel",
    "MessageDirection",
    "MessageStatus",
    "ThreadState",
    "RelationshipType",
    "MessageCategory",
    "CommitmentStatus",
    "FollowUpTrigger",
    "ResponseNeed",
    "CommunicationUrgency",
    "CommunicationTone",
    "DraftStatus",
    "RecipientType",
    "PrivacyScope",
    "RiskCategory",
    "RiskSeverity",
    "RecipientSchema",
    "AttachmentSchema",
    "ParticipantSchema",
    "RelationshipContextSchema",
    "MessageSchema",
    "ThreadSchema",
    "CommitmentSchema",
    "FollowUpSchema",
    "DraftMessageSchema",
    "DeliveryReceiptSchema",
    "SummaryResultSchema",
    "SendRequestSchema",
]
