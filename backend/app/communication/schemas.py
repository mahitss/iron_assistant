"""Pydantic v2 schemas and enums for Kairo Social & Communication Intelligence Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


# =====================================================================
# ENUMS
# =====================================================================

class CommunicationChannel(str, Enum):
    EMAIL = "EMAIL"
    CHAT = "CHAT"
    SMS = "SMS"
    MESSAGING = "MESSAGING"
    VOICE = "VOICE"
    VIDEO = "VIDEO"
    MEETING = "MEETING"
    COMMENT = "COMMENT"
    COLLABORATION = "COLLABORATION"
    NOTIFICATION = "NOTIFICATION"


class MessageDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    DRAFT = "DRAFT"
    SYSTEM = "SYSTEM"


class MessageStatus(str, Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ThreadState(str, Enum):
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"
    BLOCKED = "BLOCKED"


class RelationshipType(str, Enum):
    TEAMMATE = "TEAMMATE"
    COLLABORATOR = "COLLABORATOR"
    CLIENT = "CLIENT"
    VENDOR = "VENDOR"
    CONTACT = "CONTACT"
    FRIEND = "FRIEND"
    FAMILY = "FAMILY"
    COMMUNITY = "COMMUNITY"
    UNKNOWN = "UNKNOWN"


class MessageCategory(str, Enum):
    INFORMATION = "INFORMATION"
    QUESTION = "QUESTION"
    REQUEST = "REQUEST"
    TASK = "TASK"
    APPROVAL = "APPROVAL"
    UPDATE = "UPDATE"
    ALERT = "ALERT"
    INVITATION = "INVITATION"
    REMINDER = "REMINDER"
    COMPLAINT = "COMPLAINT"
    FEEDBACK = "FEEDBACK"
    THANKS = "THANKS"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"


class CommitmentStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class FollowUpTrigger(str, Enum):
    TIME = "TIME"
    NO_RESPONSE = "NO_RESPONSE"
    EVENT = "EVENT"
    DEADLINE = "DEADLINE"
    USER_REQUEST = "USER_REQUEST"


class ResponseNeed(str, Enum):
    NO_RESPONSE = "NO_RESPONSE"
    OPTIONAL = "OPTIONAL"
    RECOMMENDED = "RECOMMENDED"
    REQUIRED = "REQUIRED"


class CommunicationUrgency(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CommunicationTone(str, Enum):
    FORMAL = "FORMAL"
    CASUAL = "CASUAL"
    TECHNICAL = "TECHNICAL"
    CONCISE = "CONCISE"
    FRIENDLY = "FRIENDLY"
    URGENT = "URGENT"


class DraftStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    SENT = "SENT"
    DISCARDED = "DISCARDED"


class RecipientType(str, Enum):
    TO = "TO"
    CC = "CC"
    BCC = "BCC"


class PrivacyScope(str, Enum):
    PRIVATE = "PRIVATE"
    GROUP = "GROUP"
    PUBLIC = "PUBLIC"
    EXTERNAL = "EXTERNAL"


class RiskCategory(str, Enum):
    PRIVACY = "PRIVACY"
    SECURITY = "SECURITY"
    REPUTATION = "REPUTATION"
    LEGAL = "LEGAL"
    FINANCIAL = "FINANCIAL"
    MISREPRESENTATION = "MISREPRESENTATION"
    RECIPIENT = "RECIPIENT"
    CONTENT = "CONTENT"
    DELIVERY = "DELIVERY"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =====================================================================
# SCHEMAS
# =====================================================================

class RecipientSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    identity: str
    address: str
    display_name: Optional[str] = None
    recipient_type: RecipientType = RecipientType.TO
    is_external: bool = False
    organization: Optional[str] = None


class AttachmentSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    attachment_id: str = Field(default_factory=generate_uuid)
    file_name: str
    file_size_bytes: int = 0
    content_type: str = "application/octet-stream"
    checksum: Optional[str] = None
    verified_exists: bool = False
    is_sensitive: bool = False
    authorized_for_recipients: bool = True
    storage_path: Optional[str] = None


class ParticipantSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    identity: str
    display_name: str
    organization: Optional[str] = None
    role: Optional[str] = None
    authorization_scope: str = "standard"
    channel_addresses: Dict[str, str] = Field(default_factory=dict)


class RelationshipContextSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    participant_identity: str
    relationship_type: RelationshipType = RelationshipType.UNKNOWN
    project_id: Optional[str] = None
    interaction_history: List[Dict[str, Any]] = Field(default_factory=list)
    communication_preferences: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.8
    provenance: Dict[str, Any] = Field(default_factory=dict)


class MessageSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(default_factory=generate_uuid)
    channel: CommunicationChannel = CommunicationChannel.EMAIL
    sender: str
    recipients: List[RecipientSchema] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    content_reference: str
    attachments: List[AttachmentSchema] = Field(default_factory=list)
    direction: MessageDirection = MessageDirection.INBOUND
    status: MessageStatus = MessageStatus.DELIVERED
    provenance: Dict[str, Any] = Field(default_factory=dict)
    privacy_scope: PrivacyScope = PrivacyScope.PRIVATE
    user_id: str = "default_user"
    project_id: Optional[str] = None


class ThreadSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    thread_id: str = Field(default_factory=generate_uuid)
    channel: CommunicationChannel = CommunicationChannel.EMAIL
    participants: List[ParticipantSchema] = Field(default_factory=list)
    subject: str
    messages: List[MessageSchema] = Field(default_factory=list)
    state: ThreadState = ThreadState.ACTIVE
    last_activity: datetime = Field(default_factory=utc_now)
    project_id: Optional[str] = None
    importance: str = "NORMAL"
    user_id: str = "default_user"


class CommitmentSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    commitment_id: str = Field(default_factory=generate_uuid)
    statement: str
    owner: str
    due_at: Optional[datetime] = None
    source_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    status: CommitmentStatus = CommitmentStatus.OPEN
    confidence: float = 0.9
    user_id: str = "default_user"


class FollowUpSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    followup_id: str = Field(default_factory=generate_uuid)
    thread_id: str
    trigger: FollowUpTrigger = FollowUpTrigger.NO_RESPONSE
    owner: str
    due_at: datetime
    action: str
    status: str = "OPEN"
    attempts_count: int = 0
    max_attempts: int = 3
    user_id: str = "default_user"


class DraftMessageSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    draft_id: str = Field(default_factory=generate_uuid)
    thread_id: Optional[str] = None
    recipients: List[RecipientSchema] = Field(default_factory=list)
    subject: Optional[str] = None
    body_reference: str
    tone: CommunicationTone = CommunicationTone.FORMAL
    intent: str = "REQUEST"
    source_context: Dict[str, Any] = Field(default_factory=dict)
    status: DraftStatus = DraftStatus.DRAFT
    provenance: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    approved_by: Optional[str] = None
    user_id: str = "default_user"


class CommunicationRiskSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk_id: str = Field(default_factory=generate_uuid)
    message_id: Optional[str] = None
    draft_id: Optional[str] = None
    audience: PrivacyScope = PrivacyScope.PRIVATE
    category: RiskCategory = RiskCategory.CONTENT
    severity: RiskSeverity = RiskSeverity.LOW
    evidence: str = ""
    mitigation: Optional[str] = None


class DeliveryReceiptSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    receipt_id: str = Field(default_factory=generate_uuid)
    message_id: str
    channel: CommunicationChannel
    status: MessageStatus = MessageStatus.DELIVERED
    timestamp: datetime = Field(default_factory=utc_now)
    authoritative_response: Dict[str, Any] = Field(default_factory=dict)
    read_receipt: bool = False


class SummaryResultSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    what_happened: str
    decisions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    deadlines: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty_notes: List[str] = Field(default_factory=list)


class SendRequestSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    draft_id: Optional[str] = None
    channel: CommunicationChannel
    recipients: List[RecipientSchema]
    subject: Optional[str] = None
    content: str
    attachments: List[AttachmentSchema] = Field(default_factory=list)
    idempotency_key: Optional[str] = None
    user_id: str = "default_user"
    project_id: Optional[str] = None
