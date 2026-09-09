"""Pydantic schemas and enums for Kairo Unified Notification & Alerting Layer (Task 34)."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    """Canonical categories of notifications (Spec 4)."""

    TASK = "TASK"
    APPROVAL = "APPROVAL"
    SECURITY = "SECURITY"
    DEVICE = "DEVICE"
    SYSTEM = "SYSTEM"
    PROJECT = "PROJECT"
    AUTOMATION = "AUTOMATION"
    RESEARCH = "RESEARCH"
    REMINDER = "REMINDER"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class NotificationPriority(str, Enum):
    """System-enforced priority levels (Spec 5, 6, 7)."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class NotificationState(str, Enum):
    """Lifecycle states of a notification (Spec 3)."""

    PENDING = "PENDING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    READ = "READ"
    DISMISSED = "DISMISSED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ChannelType(str, Enum):
    """Supported delivery channels (Spec 28)."""

    WEB = "WEB"
    DESKTOP = "DESKTOP"
    LOCAL_COMPANION = "LOCAL_COMPANION"
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    VOICE = "VOICE"


class ActionType(str, Enum):
    """Supported notification action types (Spec 39)."""

    OPEN = "OPEN"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    CANCEL = "CANCEL"
    RETRY = "RETRY"
    REFRESH = "REFRESH"


class ActionStatus(str, Enum):
    """State of an interactive action."""

    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class DeliveryStatus(str, Enum):
    """State of a channel delivery attempt."""

    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# ---------------- Action Schemas ----------------


class NotificationActionCreate(BaseModel):
    type: ActionType
    label: str
    target_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class NotificationActionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notification_id: str
    type: ActionType
    label: str
    target_id: str
    payload: dict[str, Any] = Field(default_factory=dict, alias="payload_json")
    status: ActionStatus
    expires_at: datetime | None = None
    created_at: datetime
    executed_at: datetime | None = None


class NotificationActionExecuteRequest(BaseModel):
    action_id: str
    reason: str | None = None
    target_session_id: str | None = None


class NotificationActionExecuteResponse(BaseModel):
    action_id: str
    notification_id: str
    status: ActionStatus
    executed_at: datetime
    result: dict[str, Any] = Field(default_factory=dict)


# ---------------- Delivery Schemas ----------------


class NotificationDeliverySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notification_id: str
    channel: ChannelType
    device_id: str | None = None
    status: DeliveryStatus
    attempts: int
    delivered_at: datetime | None = None
    error_message: str | None = None


# ---------------- Core Notification Schemas ----------------


class NotificationCreateRequest(BaseModel):
    user_id: str
    project_id: str | None = None
    task_id: str | None = None
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    body: str
    expires_at: datetime | None = None
    source_event_id: str | None = None
    correlation_id: str | None = None
    dedupe_key: str | None = None
    actions: list[NotificationActionCreate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    user_id: str
    project_id: str | None = None
    task_id: str | None = None
    type: NotificationType
    priority: NotificationPriority
    title: str
    body: str
    status: NotificationState
    created_at: datetime
    expires_at: datetime | None = None
    read_at: datetime | None = None
    dismissed_at: datetime | None = None
    source_event_id: str | None = None
    correlation_id: str
    dedupe_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_json")
    actions: list[NotificationActionSchema] = Field(default_factory=list)
    deliveries: list[NotificationDeliverySchema] = Field(default_factory=list)

    @classmethod
    def from_model(cls, n: Any) -> "NotificationResponse":
        acts = []
        if hasattr(n, "__dict__") and "actions" in n.__dict__ and n.actions:
            acts = [NotificationActionSchema.model_validate(a) for a in n.actions]
        dels = []
        if hasattr(n, "__dict__") and "deliveries" in n.__dict__ and n.deliveries:
            dels = [NotificationDeliverySchema.model_validate(d) for d in n.deliveries]

        return cls(
            id=n.id,
            user_id=n.user_id,
            project_id=n.project_id,
            task_id=n.task_id,
            type=NotificationType(n.type) if isinstance(n.type, str) else n.type,
            priority=NotificationPriority(n.priority) if isinstance(n.priority, str) else n.priority,
            title=n.title,
            body=n.body,
            status=NotificationState(n.status) if isinstance(n.status, str) else n.status,
            created_at=n.created_at,
            expires_at=n.expires_at,
            read_at=n.read_at,
            dismissed_at=n.dismissed_at,
            source_event_id=n.source_event_id,
            correlation_id=n.correlation_id,
            dedupe_key=n.dedupe_key,
            metadata=getattr(n, "metadata_json", None) or {},
            actions=acts,
            deliveries=dels,
        )


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


# ---------------- Preferences Schemas ----------------


class NotificationPreferencesRequest(BaseModel):
    enabled_channels: list[ChannelType] = Field(default_factory=lambda: [ChannelType.WEB])
    type_preferences: dict[str, Any] = Field(default_factory=dict)
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    timezone: str = "UTC"
    digest_enabled: bool = False
    digest_frequency: str = "daily"
    grouping_enabled: bool = True
    min_priority: NotificationPriority = NotificationPriority.LOW


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    enabled_channels: list[str]
    type_preferences: dict[str, Any]
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    timezone: str
    digest_enabled: bool
    digest_frequency: str
    grouping_enabled: bool
    min_priority: str
    updated_at: datetime
