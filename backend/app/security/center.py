"""Central Security Center: authoritative coordinator for permissions, approvals, audit, and gates."""

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.security.approvals import ApprovalManager
from app.security.audit import AuditLogger
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.security.exceptions import (
    RateLimitExceededError,
)
from app.security.models import UserCapabilities
from app.security.permissions import Capability, PermissionLevel, get_tool_capability
from app.security.policies import SecurityDecision, evaluate_tool_policy
from app.security.rate_limits import SecurityRateLimiter
from app.security.redaction import ArgumentSanitizer
from app.security.risk import RiskLevel
from app.security.schemas import CapabilitySettingsUpdate, SecurityDecisionResult

logger = logging.getLogger("kairo.security.center")


class SecurityCenter:
    """Central authority controlling all tool execution permissions, risk, approvals, and audit."""

    def __init__(
        self,
        settings: Settings | None = None,
        emergency_stop: EmergencyStopService | None = None,
        rate_limiter: SecurityRateLimiter | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.emergency_stop = emergency_stop or get_emergency_stop_service()
        self.rate_limiter = rate_limiter or SecurityRateLimiter()

    # --- Capability Management ---

    async def get_user_capabilities(
        self,
        db_session: AsyncSession | None,
        user_id: str,
    ) -> UserCapabilities:
        """Fetch or initialize capability gates for user."""
        now = datetime.now(UTC)
        if db_session is None:
            # Return in-memory default
            return UserCapabilities(
                user_id=user_id,
                web_research=True,
                browser=bool(self.settings.KAIRO_BROWSER_ENABLED),
                voice=bool(self.settings.KAIRO_VOICE_ENABLED),
                vision=True,
                computer_control=bool(self.settings.KAIRO_COMPUTER_ENABLED),  # False by default
                developer_tools=bool(self.settings.KAIRO_DEVELOPER_ENABLED),
                automation=bool(self.settings.KAIRO_AUTOMATION_ENABLED),
                updated_at=now,
            )

        stmt = select(UserCapabilities).where(UserCapabilities.user_id == user_id)
        res = await db_session.execute(stmt)
        caps = res.scalar_one_or_none()

        if caps is None:
            caps = UserCapabilities(
                user_id=user_id,
                web_research=True,
                browser=bool(self.settings.KAIRO_BROWSER_ENABLED),
                voice=bool(self.settings.KAIRO_VOICE_ENABLED),
                vision=True,
                computer_control=bool(self.settings.KAIRO_COMPUTER_ENABLED),
                developer_tools=bool(self.settings.KAIRO_DEVELOPER_ENABLED),
                automation=bool(self.settings.KAIRO_AUTOMATION_ENABLED),
                updated_at=now,
            )
            db_session.add(caps)
            await db_session.commit()
            await db_session.refresh(caps)

        return caps

    async def update_user_capabilities(
        self,
        db_session: AsyncSession,
        user_id: str,
        updates: CapabilitySettingsUpdate,
    ) -> UserCapabilities:
        """Modify capability gates for user, emitting audit event."""
        caps = await self.get_user_capabilities(db_session, user_id)
        dump = updates.model_dump(exclude_unset=True)

        for field, val in dump.items():
            if hasattr(caps, field) and val is not None:
                setattr(caps, field, val)

        caps.updated_at = datetime.now(UTC)
        await db_session.commit()
        await db_session.refresh(caps)

        await AuditLogger.log_event(
            db_session=db_session,
            user_id=user_id,
            event_type="capability.changed",
            metadata=dump,
            success=True,
        )
        return caps

    async def is_capability_enabled(
        self,
        db_session: AsyncSession | None,
        user_id: str,
        capability: Capability | None,
    ) -> bool:
        """Check whether a capability is currently active for the given user."""
        if capability is None:
            return True

        caps = await self.get_user_capabilities(db_session, user_id)
        cap_val = capability.value
        return getattr(caps, cap_val, True)

    # --- Authorization ---

    async def authorize(
        self,
        user_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        permission_level: PermissionLevel | None = None,
        session_id: str | None = None,
        workflow_run_id: str | None = None,
        db_session: AsyncSession | None = None,
        skip_audit: bool = False,
    ) -> SecurityDecisionResult:
        """Authoritative security evaluation pipeline for a requested tool action.

        Evaluation Order:
        1. Emergency Stop check (blocks external/write/execute if stopped)
        2. User Capability Gate check (blocks disabled tool categories)
        3. Rate Limit check
        4. Central Policy & Risk classification
        5. Human-in-the-Loop Approval verification (checks for valid fingerprint approval)
        6. Append-only Audit logging
        """
        clean_args = ArgumentSanitizer.sanitize(arguments)
        fingerprint = ArgumentSanitizer.compute_action_fingerprint(
            tool_name=tool_name,
            user_id=user_id,
            session_id=session_id,
            arguments=arguments,
        )

        # 1. Emergency Stop Check
        if self.emergency_stop.is_stopped(user_id):
            if permission_level != PermissionLevel.READ:
                if not skip_audit:
                    await AuditLogger.log_event(
                        db_session=db_session,
                        user_id=user_id,
                        session_id=session_id,
                        event_type="tool.denied",
                        tool_name=tool_name,
                        risk_level=RiskLevel.HIGH.value,
                        decision=SecurityDecision.DENIED.value,
                        success=False,
                        metadata={"reason": "Emergency stop is active", "arguments": clean_args},
                    )
                return SecurityDecisionResult(
                    decision=SecurityDecision.DENIED,
                    risk_level=RiskLevel.HIGH,
                    reason="Emergency stop is ACTIVE. Side-effecting operations are blocked.",
                    action_fingerprint=fingerprint,
                )

        # 2. User Capability Gate Check
        cap = get_tool_capability(tool_name)
        if cap is not None:
            enabled = await self.is_capability_enabled(db_session, user_id, cap)
            if not enabled:
                if not skip_audit:
                    await AuditLogger.log_event(
                        db_session=db_session,
                        user_id=user_id,
                        session_id=session_id,
                        event_type="tool.denied",
                        tool_name=tool_name,
                        risk_level=RiskLevel.LOW.value,
                        decision=SecurityDecision.DENIED.value,
                        success=False,
                        metadata={"reason": f"Capability '{cap.value}' is disabled", "arguments": clean_args},
                    )
                return SecurityDecisionResult(
                    decision=SecurityDecision.DENIED,
                    risk_level=RiskLevel.LOW,
                    reason=f"Capability '{cap.value}' is disabled for user '{user_id}'.",
                    action_fingerprint=fingerprint,
                )

        # 3. Rate Limit Check
        try:
            self.rate_limiter.check_limit(
                user_id, limit_category="tool_call", max_events=60, window_seconds=60
            )
            if permission_level in (PermissionLevel.WRITE, PermissionLevel.EXTERNAL, PermissionLevel.EXECUTE):
                self.rate_limiter.check_limit(
                    user_id, limit_category="external_action", max_events=20, window_seconds=60
                )
        except RateLimitExceededError as exc:
            if not skip_audit:
                await AuditLogger.log_event(
                    db_session=db_session,
                    user_id=user_id,
                    session_id=session_id,
                    event_type="tool.denied",
                    tool_name=tool_name,
                    decision=SecurityDecision.DENIED.value,
                    success=False,
                    metadata={"reason": str(exc)},
                )
            return SecurityDecisionResult(
                decision=SecurityDecision.DENIED,
                risk_level=RiskLevel.MEDIUM,
                reason=str(exc),
                action_fingerprint=fingerprint,
            )

        # 4. Central Policy & Risk Evaluation
        policy_decision, risk = evaluate_tool_policy(tool_name, permission_level, arguments)

        if policy_decision == SecurityDecision.DENIED:
            if not skip_audit:
                await AuditLogger.log_event(
                    db_session=db_session,
                    user_id=user_id,
                    session_id=session_id,
                    event_type="tool.denied",
                    tool_name=tool_name,
                    risk_level=risk.value,
                    decision=SecurityDecision.DENIED.value,
                    success=False,
                    metadata={"reason": "Prohibited by security policy", "arguments": clean_args},
                )
            return SecurityDecisionResult(
                decision=SecurityDecision.DENIED,
                risk_level=risk,
                reason=f"Action '{tool_name}' is strictly prohibited by security policy.",
                action_fingerprint=fingerprint,
            )

        # 5. Check if Approval is Required
        if policy_decision == SecurityDecision.APPROVAL_REQUIRED:
            active_approval = None
            if db_session is not None:
                active_approval = await ApprovalManager.find_active_approval(
                    db_session=db_session,
                    user_id=user_id,
                    action_fingerprint=fingerprint,
                )

            if active_approval:
                # Prior valid approval found for exact fingerprint
                if not skip_audit:
                    await AuditLogger.log_event(
                        db_session=db_session,
                        user_id=user_id,
                        session_id=session_id,
                        event_type="tool.allowed",
                        tool_name=tool_name,
                        risk_level=risk.value,
                        decision=SecurityDecision.ALLOWED.value,
                        approval_id=active_approval.id,
                        metadata={"approved": True, "fingerprint": fingerprint},
                    )
                return SecurityDecisionResult(
                    decision=SecurityDecision.ALLOWED,
                    risk_level=risk,
                    approval_id=active_approval.id,
                    action_fingerprint=fingerprint,
                )

            # Create approval request if database session available
            approval_id = None
            if db_session is not None:
                app_req = await ApprovalManager.create_request(
                    db_session=db_session,
                    user_id=user_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    session_id=session_id,
                    workflow_run_id=workflow_run_id,
                    risk_level=risk.value,
                    timeout_seconds=self.settings.KAIRO_APPROVAL_TIMEOUT_SECONDS,
                )
                approval_id = app_req.id

            if not skip_audit:
                await AuditLogger.log_event(
                    db_session=db_session,
                    user_id=user_id,
                    session_id=session_id,
                    event_type="approval.required",
                    tool_name=tool_name,
                    risk_level=risk.value,
                    decision=SecurityDecision.APPROVAL_REQUIRED.value,
                    approval_id=approval_id,
                    metadata={"fingerprint": fingerprint, "arguments": clean_args},
                )

            return SecurityDecisionResult(
                decision=SecurityDecision.APPROVAL_REQUIRED,
                risk_level=risk,
                reason=f"Action '{tool_name}' ({risk.value} risk) requires explicit user approval.",
                approval_id=approval_id,
                action_fingerprint=fingerprint,
            )

        # 6. Action is AUTO_ALLOWED
        if not skip_audit:
            await AuditLogger.log_event(
                db_session=db_session,
                user_id=user_id,
                session_id=session_id,
                event_type="tool.allowed",
                tool_name=tool_name,
                risk_level=risk.value,
                decision=SecurityDecision.ALLOWED.value,
                metadata={"fingerprint": fingerprint},
            )

        return SecurityDecisionResult(
            decision=SecurityDecision.ALLOWED,
            risk_level=risk,
            action_fingerprint=fingerprint,
        )

    # --- Device Companion Approval Artifacts ---

    def create_device_approval_artifact(
        self,
        user_id: str,
        device_id: str,
        action: str,
        target_scope: str = "*",
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        """Generate a cryptographically verifiable approval artifact for companion execution."""
        import hmac

        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        expires_at = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=UTC)
        payload = {
            "approval_id": approval_id,
            "user_id": user_id,
            "device_id": device_id,
            "action": action,
            "target_scope": target_scope,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        signing_content = (
            f"{approval_id}:{user_id}:{device_id}:{action}:{target_scope}:{payload['expires_at']}"
        )
        secret_key = (
            self.settings.AUTH_SECRET_KEY.encode("utf-8")
            if hasattr(self.settings, "AUTH_SECRET_KEY")
            else b"kairo_approval_signing_secret"
        )
        sig = hmac.new(secret_key, signing_content.encode("utf-8"), hashlib.sha256).hexdigest()
        payload["signature"] = sig
        return payload

    def verify_device_approval_artifact(self, artifact: dict[str, Any]) -> bool:
        """Verify the integrity, scope, and expiration of a companion approval artifact."""
        import hmac

        try:
            required = [
                "approval_id",
                "user_id",
                "device_id",
                "action",
                "target_scope",
                "expires_at",
                "signature",
            ]
            if not all(k in artifact for k in required):
                return False
            expires_at = datetime.fromisoformat(artifact["expires_at"])
            if datetime.now(UTC) > expires_at:
                return False
            signing_content = (
                f"{artifact['approval_id']}:{artifact['user_id']}:{artifact['device_id']}:"
                f"{artifact['action']}:{artifact['target_scope']}:{artifact['expires_at']}"
            )
            secret_key = (
                self.settings.AUTH_SECRET_KEY.encode("utf-8")
                if hasattr(self.settings, "AUTH_SECRET_KEY")
                else b"kairo_approval_signing_secret"
            )
            expected = hmac.new(secret_key, signing_content.encode("utf-8"), hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, artifact["signature"])
        except Exception:
            return False


# Global singleton instance
_global_security_center: SecurityCenter | None = None


def get_security_center() -> SecurityCenter:
    """Retrieve or create the process-wide SecurityCenter singleton."""
    global _global_security_center
    if _global_security_center is None:
        _global_security_center = SecurityCenter()
    return _global_security_center
