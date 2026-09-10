"""Privacy controls, multi-tenancy isolation, and data redaction for Swarm Reasoning Engine (Task 64)."""

from __future__ import annotations

import re
from typing import Any

from app.swarm.safety import SwarmSafetyError, scrub_swarm_secrets


class SwarmPrivacyManager:
    """Manages context sanitization, PII masking, and multi-tenant boundary enforcement for swarm reasoning."""

    def __init__(self) -> None:
        self._email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        self._ip_pattern = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

    def sanitize_payload(self, payload: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        """Deep copy and sanitize payload, removing sensitive keys and masking PII."""
        sanitized: dict[str, Any] = {}
        for key, val in payload.items():
            if key.startswith("__") or key.lower() in (
                "secret",
                "password",
                "token",
                "private_key",
                "credentials",
            ):
                sanitized[key] = "[REDACTED]"
            elif isinstance(val, str):
                sanitized[key] = self.mask_pii(scrub_swarm_secrets(val))
            elif isinstance(val, dict):
                sanitized[key] = self.sanitize_payload(val, tenant_id=tenant_id)
            elif isinstance(val, list):
                sanitized[key] = [
                    self.sanitize_payload(item, tenant_id=tenant_id)
                    if isinstance(item, dict)
                    else (self.mask_pii(scrub_swarm_secrets(item)) if isinstance(item, str) else item)
                    for item in val
                ]
            else:
                sanitized[key] = val
        if tenant_id:
            sanitized["_tenant_id"] = tenant_id
        return sanitized

    def mask_pii(self, text: str) -> str:
        """Mask emails and IP addresses."""
        if not text:
            return text
        masked = self._email_pattern.sub("[REDACTED_EMAIL]", text)
        masked = self._ip_pattern.sub("[REDACTED_IP]", masked)
        return masked

    def validate_tenant_access(
        self,
        swarm_tenant: str,
        current_tenant: str,
        is_admin: bool = False,
    ) -> bool:
        """Enforce strict tenant isolation on swarm sessions, tasks, and results."""
        return validate_tenant_access(
            target_tenant=swarm_tenant,
            session_tenant=current_tenant,
            is_admin=is_admin,
        )


def mask_pii(text: str) -> str:
    """Module-level helper to mask PII."""
    return swarm_privacy_manager.mask_pii(text)


def validate_tenant_access(
    target_tenant: str,
    session_tenant: str,
    is_admin: bool = False,
) -> bool:
    """Module-level tenant isolation check, raising SwarmSafetyError on cross-tenant mismatch."""
    if is_admin or target_tenant == session_tenant:
        return True
    raise SwarmSafetyError(f"Cross-tenant access violation: {session_tenant} cannot access {target_tenant}")


swarm_privacy_manager = SwarmPrivacyManager()
