"""Pydantic request and response schemas for Security Center."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.security.policies import SecurityDecision
from app.security.risk import RiskLevel


class CapabilitySettingsUpdate(BaseModel):
    """Payload to update user capability toggles."""

    web_research: bool | None = None
    browser: bool | None = None
    voice: bool | None = None
    vision: bool | None = None
    computer_control: bool | None = None
    developer_tools: bool | None = None
    automation: bool | None = None


class UserCapabilitiesResponse(BaseModel):
    """Current capability toggles for user."""

    user_id: str
    web_research: bool
    browser: bool
    voice: bool
    vision: bool
    computer_control: bool
    developer_tools: bool
    automation: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalDecisionRequest(BaseModel):
    """Payload for user approve or deny action."""

    decision: Literal["approve", "deny"]
    reason: str | None = Field(default=None, max_length=500)


class ApprovalRequestResponse(BaseModel):
    """Details of an approval request."""

    id: str
    user_id: str
    session_id: str | None = None
    workflow_run_id: str | None = None
    tool_name: str
    action_description: str
    risk_level: str
    arguments_summary: dict[str, Any]
    status: str
    expires_at: datetime
    created_at: datetime
    decided_at: datetime | None = None
    decision_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditEventResponse(BaseModel):
    """Representation of an audit event."""

    id: str
    user_id: str
    session_id: str | None = None
    timestamp: datetime
    event_type: str
    tool_name: str | None = None
    risk_level: str | None = None
    decision: str | None = None
    approval_id: str | None = None
    success: bool | None = None
    metadata_json: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class AuditQueryResponse(BaseModel):
    """Paginated list of audit events."""

    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int


class EmergencyStopResponse(BaseModel):
    """Status of the emergency kill switch."""

    is_stopped: bool
    status: Literal["STOPPED", "ACTIVE"]
    timestamp: str | None = None
    reason: str | None = None


class EmergencyStopActionRequest(BaseModel):
    """Request payload to trigger emergency stop."""

    reason: str = Field(default="User initiated stop", max_length=250)


class SecurityDecisionResult(BaseModel):
    """Structured decision returned by SecurityCenter.authorize()."""

    decision: SecurityDecision
    risk_level: RiskLevel
    reason: str = ""
    approval_id: str | None = None
    action_fingerprint: str | None = None
