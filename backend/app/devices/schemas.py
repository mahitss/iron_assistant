"""Pydantic schemas for Kairo Device Runtime and Local Companion APIs."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeviceStatus(str, Enum):
    """Device lifecycle states."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    DISABLED = "DISABLED"


class DeviceCapabilitiesSchema(BaseModel):
    """Granular device capability toggles."""

    computer_control: bool = Field(default=False, description="Computer control (mouse/keyboard) enabled")
    voice: bool = Field(default=False, description="Voice microphone / wake-word enabled")
    camera: bool = Field(default=False, description="Camera capture enabled")
    filesystem: bool = Field(default=False, description="Sandboxed filesystem access enabled")


class DeviceRegisterRequest(BaseModel):
    """Payload for registering a companion runtime with Kairo."""

    device_id: str | None = Field(
        default=None, description="Optional client-generated persistent device UUID"
    )
    device_name: str = Field(..., min_length=1, max_length=128, description="Human-readable device name")
    os_name: str = Field(..., description="OS platform: windows, darwin, or linux")
    os_version: str = Field(default="unknown", description="Operating system version/build")
    companion_version: str = Field(default="1.1.0", description="Companion runtime version")
    public_key: str | None = Field(default=None, description="Public key for signature verification")
    allowed_paths: list[str] = Field(
        default_factory=list, description="Initial approved workspace directories"
    )


class DeviceRegisterResponse(BaseModel):
    """Response returned upon successful device registration."""

    device_id: str
    device_name: str
    status: DeviceStatus
    device_token: str = Field(..., description="Secret authentication token for the companion runtime")
    capabilities: DeviceCapabilitiesSchema
    allowed_paths: list[str]
    created_at: datetime


class DeviceResponse(BaseModel):
    """Authoritative device metadata representation."""

    model_config = ConfigDict(from_attributes=True)

    device_id: str
    user_id: str
    device_name: str
    client_type: str = "LOCAL_COMPANION"
    os_name: str
    os_version: str
    companion_version: str
    status: DeviceStatus
    trust_status: str = "UNTRUSTED"
    capabilities: DeviceCapabilitiesSchema
    declared_capabilities: list[str] = Field(default_factory=list)
    allowed_paths: list[str]
    created_at: datetime
    last_seen_at: datetime
    trust_expires_at: datetime | None = None
    revoked_at: datetime | None = None


class DeviceUpdateRequest(BaseModel):
    """Payload for updating device capabilities or configuration."""

    device_name: str | None = Field(default=None, max_length=128)
    computer_control_enabled: bool | None = None
    voice_enabled: bool | None = None
    camera_enabled: bool | None = None
    filesystem_enabled: bool | None = None
    allowed_paths: list[str] | None = None
    status: DeviceStatus | None = None


class DeviceCommandRequest(BaseModel):
    """Payload for dispatching a structured allowlisted action to a companion device."""

    action: str = Field(..., description="Allowlisted action name (e.g. screen.capture, mouse.click)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")
    authorization_context: str | None = Field(
        default=None, description="Cryptographic or signed approval context"
    )


class DeviceCommandResponse(BaseModel):
    """Status of a dispatched device action."""

    command_id: str
    device_id: str
    action: str
    status: str = Field(default="DISPATCHED", description="DISPATCHED, PENDING_APPROVAL, or REJECTED")
    approval_required: bool = False
    approval_id: str | None = None
    dispatched_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class DeviceEventSchema(BaseModel):
    """Telemetry and security events emitted by companion devices."""

    event_id: str
    event_type: str
    device_id: str
    user_id: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)
