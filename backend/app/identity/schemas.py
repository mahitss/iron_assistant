"""Pydantic schemas and enums for Kairo Identity, Sessions, Device Trust, Presence, and Handoff."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ClientType(str, Enum):
    """Authorized interface client types (Spec 5)."""
    WEB = "WEB"
    DESKTOP = "DESKTOP"
    MOBILE = "MOBILE"
    VOICE = "VOICE"
    API = "API"
    LOCAL_COMPANION = "LOCAL_COMPANION"


class SessionStatus(str, Enum):
    """Session lifecycle state (Spec 4)."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class DeviceStatus(str, Enum):
    """Operational state of a registered device (Spec 11)."""
    ACTIVE = "ACTIVE"
    OFFLINE = "OFFLINE"
    REVOKED = "REVOKED"
    PENDING = "PENDING"


class DeviceTrustStatus(str, Enum):
    """Explicit trust level of a device (Spec 12)."""
    UNTRUSTED = "UNTRUSTED"
    PENDING = "PENDING"
    TRUSTED = "TRUSTED"
    REVOKED = "REVOKED"


class PresenceState(str, Enum):
    """Application-level interface presence (Spec 21)."""
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    DISCONNECTED = "DISCONNECTED"


class DeviceCapability(str, Enum):
    """Hardware capabilities a device runtime can advertise (Spec 19)."""
    SCREEN = "SCREEN"
    MICROPHONE = "MICROPHONE"
    CAMERA = "CAMERA"
    KEYBOARD = "KEYBOARD"
    MOUSE = "MOUSE"
    AUDIO_OUTPUT = "AUDIO_OUTPUT"
    FILE_ACCESS = "FILE_ACCESS"


class IdentityErrorCode(str, Enum):
    """Standard error codes (Spec 115)."""
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_REVOKED = "SESSION_REVOKED"
    DEVICE_UNTRUSTED = "DEVICE_UNTRUSTED"
    DEVICE_REVOKED = "DEVICE_REVOKED"
    CAPABILITY_UNAUTHORIZED = "CAPABILITY_UNAUTHORIZED"
    HANDOFF_EXPIRED = "HANDOFF_EXPIRED"
    HANDOFF_INVALID = "HANDOFF_INVALID"
    DEVICE_UNAVAILABLE = "DEVICE_UNAVAILABLE"
    AMBIGUOUS_DEVICE = "AMBIGUOUS_DEVICE"
    AMBIGUOUS_TARGET = "AMBIGUOUS_TARGET"


# --- Session Schemas ---

class SessionCreateRequest(BaseModel):
    client_type: ClientType
    device_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="ignore")


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    client_type: ClientType
    device_id: str | None = None
    status: SessionStatus
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)


class SessionRevokeRequest(BaseModel):
    reason: str = "User initiated revocation"


# --- Device Trust & Pairing Schemas ---

class DeviceTrustUpdateRequest(BaseModel):
    trust_status: DeviceTrustStatus = DeviceTrustStatus.TRUSTED
    expires_in_days: int | None = 90
    model_config = ConfigDict(extra="ignore")


class DevicePairingRequest(BaseModel):
    device_name: str | None = None
    client_type: ClientType = ClientType.LOCAL_COMPANION
    capabilities: list[DeviceCapability] = Field(default_factory=list)
    model_config = ConfigDict(extra="ignore")


class DevicePairingResponse(BaseModel):
    pairing_code: str
    device_id: str
    expires_at: datetime
    instructions: str


class DevicePairingConsumeRequest(BaseModel):
    pairing_code: str
    device_id: str
    public_key: str | None = None
    model_config = ConfigDict(extra="ignore")


# --- Presence Schemas ---

class PresenceUpdateRequest(BaseModel):
    session_id: str
    device_id: str | None = None
    interface: str
    state: PresenceState = PresenceState.ACTIVE
    model_config = ConfigDict(extra="ignore")


class PresenceResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    device_id: str | None = None
    interface: str
    state: PresenceState
    last_seen_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserOnlineStatus(BaseModel):
    user_id: str
    status_text: str  # "Kairo session active" or "Offline"
    active_sessions_count: int
    presence: list[PresenceResponse]


# --- Handoff Schemas ---

class HandoffCreateRequest(BaseModel):
    source_session_id: str
    target_device_id: str | None = None
    conversation_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    explicit_consent: bool = True
    model_config = ConfigDict(extra="ignore")


class HandoffResponse(BaseModel):
    handoff_id: str
    handoff_token: str
    expires_at: datetime
    target_device_id: str | None = None


class HandoffCompleteRequest(BaseModel):
    handoff_token: str
    target_session_id: str
    model_config = ConfigDict(extra="ignore")


class HandoffContextPacket(BaseModel):
    handoff_id: str
    user_id: str
    source_session_id: str
    target_session_id: str | None = None
    conversation_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    relevant_context: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="ignore")
