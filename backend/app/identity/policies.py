"""Security policies and invariant enforcement for Kairo Identity, Sessions, and Device Trust."""

from datetime import UTC, datetime
import logging
from typing import Any

from app.identity.models import IdentitySessionModel
from app.identity.schemas import ClientType, DeviceCapability, DeviceTrustStatus, IdentityErrorCode, SessionStatus
from app.security.exceptions import (
    CapabilityDisabledError,
    EmergencyStopActiveError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)

logger = logging.getLogger("kairo.identity.policies")


class IdentityPolicyEnforcer:
    """Authoritative invariant enforcement governing Sessions, Device Trust, and Capabilities."""

    @classmethod
    def enforce_session_active(cls, session: IdentitySessionModel, idle_timeout_seconds: int = 3600) -> None:
        """Validate that a session is strictly active and within expiration and idle boundaries."""
        if not session:
            raise SecurityPolicyViolationError(IdentityErrorCode.SESSION_REVOKED.value)

        if session.status == SessionStatus.REVOKED.value:
            logger.warning("Access denied: Session '%s' is REVOKED.", session.session_id)
            raise SecurityPolicyViolationError(IdentityErrorCode.SESSION_REVOKED.value)

        now = datetime.now(UTC)
        exp = session.expires_at if session.expires_at.tzinfo is not None else session.expires_at.replace(tzinfo=UTC)
        if session.status == SessionStatus.EXPIRED.value or now > exp:
            logger.info("Access denied: Session '%s' is EXPIRED (absolute TTL).", session.session_id)
            raise SecurityPolicyViolationError(IdentityErrorCode.SESSION_EXPIRED.value)

        last_act = session.last_activity_at if session.last_activity_at.tzinfo is not None else session.last_activity_at.replace(tzinfo=UTC)
        idle_duration = (now - last_act).total_seconds()
        if idle_duration > idle_timeout_seconds:
            logger.info("Access denied: Session '%s' timed out (idle for %ds).", session.session_id, idle_duration)
            session.status = SessionStatus.EXPIRED.value
            raise SecurityPolicyViolationError(IdentityErrorCode.SESSION_EXPIRED.value)

    @classmethod
    def enforce_device_trust(
        cls,
        device_status: str,
        trust_status: str,
        trust_expires_at: datetime | None = None,
        required_trust: DeviceTrustStatus = DeviceTrustStatus.TRUSTED,
    ) -> None:
        """Enforce explicit device trust requirements without assuming trust implies permission (Spec 12, 13)."""
        raw_status = (device_status or "").upper()
        raw_trust = (trust_status or "").upper()

        if raw_status == "REVOKED" or raw_trust == "REVOKED":
            logger.warning("Operation blocked: Device is REVOKED.")
            raise SecurityPolicyViolationError(IdentityErrorCode.DEVICE_REVOKED.value)

        if raw_trust != required_trust.value:
            logger.warning("Operation blocked: Device trust '%s' does not meet required '%s'.", raw_trust, required_trust.value)
            raise SecurityPolicyViolationError(IdentityErrorCode.DEVICE_UNTRUSTED.value)

        if trust_expires_at:
            t_exp = trust_expires_at if trust_expires_at.tzinfo is not None else trust_expires_at.replace(tzinfo=UTC)
            if datetime.now(UTC) > t_exp:
                logger.warning("Operation blocked: Device trust expired at %s.", trust_expires_at)
                raise SecurityPolicyViolationError(IdentityErrorCode.DEVICE_UNTRUSTED.value)

    @classmethod
    def enforce_capability_vs_permission(
        cls,
        device_declared_capabilities: list[str],
        requested_capability: str,
        security_center_authorized: bool,
    ) -> None:
        """
        Enforce the critical separation:
        Device capability != Permission (Spec 20, 54, 154).
        Even if hardware supports capability, SecurityCenter must explicitly authorize it.
        """
        req = requested_capability.upper()
        # 1. Device hardware check
        has_hardware = any(c.upper() == req for c in device_declared_capabilities)
        if not has_hardware:
            logger.warning("Capability '%s' not advertised by device hardware.", req)
            raise CapabilityDisabledError(f"Device does not support capability '{req}'.")

        # 2. Security Center authorization check
        if not security_center_authorized:
            logger.warning("Capability '%s' denied by SecurityCenter policy.", req)
            raise SecurityPolicyViolationError(IdentityErrorCode.CAPABILITY_UNAUTHORIZED.value)

    @classmethod
    def enforce_tenant_isolation(cls, current_user_id: str, resource_owner_id: str, resource_name: str = "resource") -> None:
        """Enforce tenant isolation across users (User A cannot access User B's resources, Spec 6, 147)."""
        if current_user_id != resource_owner_id:
            logger.critical(
                "Cross-user violation attempt: user '%s' tried to access %s owned by '%s'.",
                current_user_id,
                resource_name,
                resource_owner_id,
            )
            raise TenantIsolationError(f"Access denied: {resource_name} belongs to another user.")

    @classmethod
    def enforce_emergency_stop(cls, user_id: str | None = None) -> None:
        """Check emergency stop status, overriding all sessions and device actions (Spec 72, 73, 157)."""
        try:
            from app.security.center import get_security_center
            sec_center = get_security_center()
            if sec_center and sec_center.emergency_stop:
                is_active = sec_center.emergency_stop.is_stopped(user_id=user_id)
                if is_active:
                    raise EmergencyStopActiveError("Emergency stop is active. Privileged operations are strictly blocked.")
        except ImportError:
            pass
