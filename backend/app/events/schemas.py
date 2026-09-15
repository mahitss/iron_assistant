"""
Canonical data models and schemas for Kairo Unified Event Bus and Event-Driven Runtime.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
import re
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventSource(str, Enum):
    """Authoritative source originating the event."""

    CHAT = "chat"
    AGENT = "agent"
    SKILL = "skill"
    TOOL = "tool"
    SECURITY = "security"
    APPROVAL = "approval"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    PROJECT = "project"
    GITHUB = "github"
    RESEARCH = "research"
    WORKFLOW = "automation"
    PROACTIVE = "proactive"
    NOTIFICATION = "notification"
    DEVICE = "device"
    VOICE = "voice"
    VISION = "vision"
    COMPUTER = "computer"
    SYSTEM = "system"
    PROVIDER = "provider"
    EXPERIENCE = "experience"
    FEEDBACK = "feedback"
    MULTIMODAL = "multimodal"
    TASK = "task"
    WORLD = "world"
    IDENTITY = "identity"

    # Common integration sources
    GITHUB_WEBHOOK = "github_webhook"
    CHAT_ROUTER = "chat_router"
    SECURITY_CENTER = "security_center"
    APPROVAL_MANAGER = "approval_manager"
    API_CLIENT = "api_client"
    TEST = "test"
    DEAD_LETTER_REPLAY = "dead_letter_replay"
    OUTBOX_PROCESSOR = "outbox_processor"


class ReplaySafety(str, Enum):
    """Replay safety classification preventing duplicate side-effects (Section 19 & 20)."""

    REPLAY_SAFE = "REPLAY_SAFE"
    REPLAY_REQUIRES_REVIEW = "REPLAY_REQUIRES_REVIEW"
    NON_REPLAYABLE = "NON_REPLAYABLE"


class EventStatus(str, Enum):
    """Lifecycle dispatch status of an event."""

    PUBLISHED = "PUBLISHED"
    DELIVERED = "DELIVERED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class EventMetadata(BaseModel):
    """Operational telemetry and tracing metadata for an event."""

    model_config = ConfigDict(extra="allow")

    environment: str = "production"
    attempts: int = 1
    trace_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    emitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


import time


class EventSeverity(str, Enum):
    """Deterministic severity classification for events (Section 10)."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @property
    def priority_tier(self) -> int:
        if self == EventSeverity.CRITICAL:
            return 0
        if self in (EventSeverity.ERROR, EventSeverity.WARNING):
            return 1
        if self in (EventSeverity.NOTICE, EventSeverity.INFO):
            return 2
        return 3


class EventClassification(str, Enum):
    """Broad categorization dictating storage, redaction, and UI visibility (Section 11)."""

    INTERNAL = "INTERNAL"
    SECURITY = "SECURITY"
    AUDIT = "AUDIT"
    OPERATIONAL = "OPERATIONAL"
    PERFORMANCE = "PERFORMANCE"
    DIAGNOSTIC = "DIAGNOSTIC"
    USER_VISIBLE = "USER_VISIBLE"
    SYSTEM = "SYSTEM"


class EventOutcome(str, Enum):
    """Observability outcome classification. Observability reports, never decides auth (Section 1)."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    BLOCK = "BLOCK"
    FAIL = "FAIL"
    CANCEL = "CANCEL"
    TIMEOUT = "TIMEOUT"
    SUCCESS = "SUCCESS"
    UNKNOWN = "UNKNOWN"


class PrivacyClass(str, Enum):
    """Explicit privacy sensitivity classification (Section 12)."""

    PUBLIC_SAFE = "PUBLIC_SAFE"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    SECRET = "SECRET"
    RESTRICTED = "RESTRICTED"


class RetentionClass(str, Enum):
    """Lifecycle retention classification (Section 45)."""

    AUDIT_CRITICAL = "AUDIT_CRITICAL"
    OPERATIONAL = "OPERATIONAL"
    DIAGNOSTIC = "DIAGNOSTIC"
    EPHEMERAL = "EPHEMERAL"


class ExecutionDomain(str, Enum):
    """Unified execution domains across Python and Rust (Section 3)."""

    RUNTIME = "runtime"
    EXECUTION = "execution"
    RESOURCE = "resource"
    SECURITY = "security"
    COMPUTER = "computer"
    NETWORK = "network"
    GOVERNANCE = "governance"
    WORKFLOW = "workflow"
    TOOL = "tool"
    LEARNING = "learning"
    HEALTH = "health"
    SYSTEM = "system"


class Event(BaseModel):
    """Canonical model for all Kairo internal events (Section 2, 3, 4, 5, 7, 8, 9)."""

    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Globally unique UUID identifying this specific event instance",
    )
    event_type: str = Field(
        ...,
        description="Hierarchical namespaced event name (e.g. 'github.ci.failed')",
    )
    event_version: str = Field(
        default="v1",
        description="Schema contract version (e.g. 'v1')",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when event occurred",
    )
    monotonic_timestamp: float = Field(
        default_factory=time.perf_counter,
        description="Monotonic clock timestamp for precise duration measurement",
    )
    source: EventSource | str = Field(
        ...,
        description="Trusted system component that emitted the event",
    )
    user_id: str | None = Field(
        default=None,
        description="Owning user identifier for tenant isolation",
    )
    project_id: str | None = Field(
        default=None,
        description="Active project identifier where applicable",
    )
    correlation_id: str = Field(
        default_factory=lambda: f"corr_{uuid.uuid4().hex[:12]}",
        description="Shared correlation ID tracing a complete user request lifecycle",
    )
    causation_id: str | None = Field(
        default=None,
        description="Event ID that directly triggered or caused this event",
    )
    parent_event_id: str | None = Field(
        default=None,
        description="Parent event ID for hierarchical lifecycle relationships",
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed execution trace identifier",
    )
    span_id: str | None = Field(
        default=None,
        description="Distributed execution span identifier",
    )
    request_id: str | None = Field(
        default=None,
        description="Originating request identifier",
    )
    workflow_id: str | None = Field(
        default=None,
        description="Enclosing workflow identifier",
    )
    run_id: str | None = Field(
        default=None,
        description="Execution run identifier",
    )
    task_id: str | None = Field(
        default=None,
        description="Autonomous task identifier",
    )
    tool_id: str | None = Field(
        default=None,
        description="Active tool identifier",
    )
    capability_id: str | None = Field(
        default=None,
        description="Substrate capability identifier",
    )
    actor_type: str | None = Field(
        default=None,
        description="Type of actor (user, agent, system, native_runtime)",
    )
    actor_id: str | None = Field(
        default=None,
        description="Identifier of actor initiating action",
    )
    execution_domain: ExecutionDomain | str = Field(
        default=ExecutionDomain.SYSTEM,
        description="Subsystem execution domain",
    )
    severity: EventSeverity = Field(
        default=EventSeverity.INFO,
        description="Deterministic severity classification",
    )
    classification: EventClassification = Field(
        default=EventClassification.INTERNAL,
        description="Data classification level",
    )
    outcome: EventOutcome | None = Field(
        default=None,
        description="Outcome reported by the event (reports, never authorizes)",
    )
    provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="Subsystem provenance, host metadata, and runtime instance",
    )
    privacy_class: PrivacyClass = Field(
        default=PrivacyClass.INTERNAL,
        description="Privacy sensitivity classification",
    )
    retention_class: RetentionClass = Field(
        default=RetentionClass.OPERATIONAL,
        description="Retention lifecycle policy classification",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific event data payload",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Tracing and runtime operational metadata",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+(\.[a-zA-Z0-9_\-]+)+$", v):
            raise ValueError(
                f"Event type '{v}' must be namespaced lowercase dot-separated (e.g. 'github.ci.failed')."
            )
        return v

    @field_validator("payload", mode="before")
    @classmethod
    def validate_and_bound_payload(cls, v: Any) -> dict[str, Any]:
        if not isinstance(v, dict):
            return {"value": str(v)[:2048]}

        # Bound attribute count
        if len(v) > 100:
            truncated = dict(list(v.items())[:100])
            truncated["_truncated_attributes"] = True
            truncated["_original_attribute_count"] = len(v)
            v = truncated

        import json
        try:
            raw = json.dumps(v, default=str)
            if len(raw) > 65_536:
                import hashlib
                payload_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                return {
                    "_payload_truncated": True,
                    "_original_size_bytes": len(raw),
                    "_payload_sha256": payload_hash,
                    "preview": {k: str(val)[:256] for k, val in list(v.items())[:20]},
                }
        except Exception:
            pass

        return v

    @property
    def priority_tier(self) -> int:
        """Priority tier 0 (P0 Critical), 1 (P1 Error/Security), 2 (P2 Info/Lifecycle), 3 (P3 Debug)."""
        if self.event_type.startswith("emergency_stop.") or self.severity == EventSeverity.CRITICAL:
            return 0
        if self.severity in (EventSeverity.ERROR, EventSeverity.WARNING) or self.classification in (
            EventClassification.SECURITY,
            EventClassification.AUDIT,
        ):
            return 1
        if self.severity in (EventSeverity.NOTICE, EventSeverity.INFO):
            return 2
        return 3


# --- Typed Payloads for Canonical Event Types ---


class GithubCiFailedPayload(BaseModel):
    """Payload for github.ci.failed event."""

    model_config = ConfigDict(extra="allow")

    repo: str | None = None
    repository: str | None = None
    branch: str = "main"
    commit_sha: str = "HEAD"
    workflow_name: str = "CI"
    failing_step: str = "build"
    check_run_id: str | int | None = None
    failure_summary: str | None = None
    error_summary: str | None = None
    run_id: str | int | None = None
    log_snippet: str | None = None

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.repository and self.repo:
            self.repository = self.repo
        if not self.repo and self.repository:
            self.repo = self.repository
        if not self.error_summary and self.failure_summary:
            self.error_summary = self.failure_summary
        if not self.failure_summary and self.error_summary:
            self.failure_summary = self.error_summary


class ChatMessageCreatedPayload(BaseModel):
    """Payload for chat.message.created event."""

    model_config = ConfigDict(extra="allow")

    session_id: str | None = None
    message_id: str | None = None
    message: str | None = None
    role: str = "user"
    content_length: int = 0
    has_attachments: bool = False


class ChatResponseCompletedPayload(BaseModel):
    """Payload for chat.response.completed event."""

    model_config = ConfigDict(extra="allow")

    session_id: str | None = None
    message_id: str | None = None
    tokens_used: int = 0
    duration_ms: float = 0.0
    model_id: str | None = None


class SecurityBlockedPayload(BaseModel):
    """Payload for security.blocked event."""

    model_config = ConfigDict(extra="allow")

    tool_name: str = "unknown"
    risk_level: str = "HIGH"
    reason: str = "Blocked by security policy"
    action_fingerprint: str | None = None


class ApprovalRequestedPayload(BaseModel):
    """Payload for approval.requested event."""

    model_config = ConfigDict(extra="allow")

    approval_id: str = ""
    tool_name: str = ""
    risk_level: str = "HIGH"
    action_fingerprint: str = ""
    action: str | None = None


class ApprovalGrantedPayload(BaseModel):
    """Payload for approval.granted event."""

    model_config = ConfigDict(extra="allow")

    approval_id: str = ""
    decided_by: str = ""
    action_fingerprint: str = ""
    action: str | None = None


class EmergencyStopActivatedPayload(BaseModel):
    """Payload for emergency_stop.activated event."""

    model_config = ConfigDict(extra="allow")

    reason: str = "Emergency stop activated"
    triggered_by: str = "system"


class DeviceConnectedPayload(BaseModel):
    """Payload for device.connected event."""

    model_config = ConfigDict(extra="allow")

    device_id: str = ""
    device_name: str = "Companion Device"
    device_type: str = "companion"
    capabilities: list[str] = Field(default_factory=list)


class NotificationCreatedPayload(BaseModel):
    """Payload for notification.created event."""

    model_config = ConfigDict(extra="allow")

    notification_id: str = ""
    title: str = "Notification"
    body: str = ""
    priority: str = "normal"
    category: str = "general"


class DeadLetterRecord(BaseModel):
    """Representation of an event moved to dead-letter queue after retries exhausted."""

    dead_letter_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event: Event
    handler_name: str
    attempts: int
    last_error: str
    failed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    replay_safety: ReplaySafety = ReplaySafety.REPLAY_REQUIRES_REVIEW
    replayed_at: datetime | None = None
    replayed_by: str | None = None


def validate_and_bound_payload(payload: Any, max_bytes: int = 65536, max_attributes: int = 100) -> dict[str, Any]:
    """Helper function to validate and bound event payloads (Task 86)."""
    return Event.validate_and_bound_payload(payload)

