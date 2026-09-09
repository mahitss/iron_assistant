"""Kairo Identity, Session Continuity, Device Trust, Presence, and Handoff Subsystem (Task 33)."""

from app.identity.devices import IdentityDeviceManager
from app.identity.handoff import HandoffManager
from app.identity.identity import IdentityContext, IdentityResolverService
from app.identity.models import HandoffContextModel, IdentityPresenceModel, IdentitySessionModel
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.presence import PresenceTracker
from app.identity.resolver import IdentityResolver
from app.identity.revocation import RevocationCoordinator
from app.identity.schemas import (
    ClientType,
    DeviceCapability,
    DevicePairingConsumeRequest,
    DevicePairingRequest,
    DevicePairingResponse,
    DeviceStatus,
    DeviceTrustStatus,
    DeviceTrustUpdateRequest,
    HandoffCompleteRequest,
    HandoffContextPacket,
    HandoffCreateRequest,
    HandoffResponse,
    IdentityErrorCode,
    PresenceResponse,
    PresenceState,
    PresenceUpdateRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionRevokeRequest,
    SessionStatus,
    UserOnlineStatus,
)
from app.identity.sessions import SessionManager
from app.identity.tokens import (
    generate_handoff_token,
    generate_pairing_code,
    generate_session_token,
    hash_token,
    mask_token,
    verify_token,
)
from app.identity.trust import DeviceTrustManager

__all__ = [
    "ClientType",
    "SessionStatus",
    "DeviceStatus",
    "DeviceTrustStatus",
    "PresenceState",
    "DeviceCapability",
    "IdentityErrorCode",
    "IdentitySessionModel",
    "IdentityPresenceModel",
    "HandoffContextModel",
    "SessionCreateRequest",
    "SessionResponse",
    "SessionRevokeRequest",
    "DeviceTrustUpdateRequest",
    "DevicePairingRequest",
    "DevicePairingResponse",
    "DevicePairingConsumeRequest",
    "PresenceUpdateRequest",
    "PresenceResponse",
    "UserOnlineStatus",
    "HandoffCreateRequest",
    "HandoffResponse",
    "HandoffCompleteRequest",
    "HandoffContextPacket",
    "IdentityContext",
    "IdentityResolverService",
    "IdentityPolicyEnforcer",
    "SessionManager",
    "IdentityDeviceManager",
    "DeviceTrustManager",
    "PresenceTracker",
    "HandoffManager",
    "RevocationCoordinator",
    "IdentityResolver",
    "hash_token",
    "verify_token",
    "generate_session_token",
    "generate_pairing_code",
    "generate_handoff_token",
    "mask_token",
]
