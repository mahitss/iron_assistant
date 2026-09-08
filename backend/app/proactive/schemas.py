"""Pydantic request and response schemas for Proactive Intelligence."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.proactive.state import Actionability, InsightPriority, SourceType


class UserProactiveSettingsRead(BaseModel):
    """User proactive notification settings and preferences."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    proactive_enabled: bool = True
    notify_on_workflow_failure: bool = True
    notify_on_ci_failure: bool = True
    notify_on_approval: bool = True
    notify_on_web_change: bool = True
    minimum_priority: str = "LOW"
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    timezone: str = "UTC"
    updated_at: datetime | None = None


class UserProactiveSettingsUpdate(BaseModel):
    """Payload to update user proactive preferences."""

    proactive_enabled: bool | None = None
    notify_on_workflow_failure: bool | None = None
    notify_on_ci_failure: bool | None = None
    notify_on_approval: bool | None = None
    notify_on_web_change: bool | None = None
    minimum_priority: str | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None


class CandidateInsight(BaseModel):
    """An event candidate identified by ProactiveDetector before filtering."""

    user_id: str
    source_type: SourceType | str
    source_id: str | None = None
    category: str
    title: str
    summary: str
    priority: InsightPriority | str = InsightPriority.MEDIUM
    actionability: Actionability | str = Actionability.INFORMATIONAL
    action_payload: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str | None = None
    chain_depth: int = 0
    state_key: str | None = None
    state_value: str | None = None
    expires_at: datetime | None = None


class ProactiveInsightRead(BaseModel):
    """Surfaced proactive insight representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    source_type: str
    source_id: str | None = None
    title: str
    summary: str
    priority: str
    actionability: str
    status: str
    action_payload: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str
    created_at: datetime
    expires_at: datetime | None = None


class ProactiveFeedResponse(BaseModel):
    """Ranked feed response of active proactive insights."""

    items: list[ProactiveInsightRead]
    total: int
    unread_count: int


class NotificationRead(BaseModel):
    """In-app notification item representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    source_type: str
    source_id: str | None = None
    title: str
    summary: str
    priority: str
    actionability: str
    status: str
    action_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime | None = None


class NotificationActionResponse(BaseModel):
    """Response when updating a notification's status (read/dismiss)."""

    id: str
    status: str
    user_id: str


class WebMonitorCreate(BaseModel):
    """Configuration to create a new monitored URL."""

    name: str = Field(..., min_length=1, max_length=128)
    url: str = Field(..., min_length=4, max_length=512)
    check_interval_seconds: int = Field(default=3600, ge=60, le=86400 * 7)
    enabled: bool = True


class WebMonitorUpdate(BaseModel):
    """Configuration updates for a monitored URL."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    url: str | None = Field(default=None, min_length=4, max_length=512)
    check_interval_seconds: int | None = Field(default=None, ge=60, le=86400 * 7)
    enabled: bool | None = None


class WebMonitorRead(BaseModel):
    """Monitored URL model response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    url: str
    check_interval_seconds: int
    content_fingerprint: str | None = None
    enabled: bool
    last_checked_at: datetime | None = None
    created_at: datetime


class WebMonitorCheckResult(BaseModel):
    """Output from evaluating a web monitor for content changes."""

    monitor_id: str
    url: str
    changed: bool
    old_fingerprint: str | None = None
    new_fingerprint: str
    checked_at: datetime
    error: str | None = None
