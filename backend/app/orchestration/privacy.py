"""Privacy controls, multi-tenancy context isolation, and data redaction for Orchestration (Task 59)."""

from __future__ import annotations

import re
from typing import Any


class OrchestrationPrivacyManager:
    """Manages privacy boundaries, tenant isolation, and sensitive data protection."""

    def __init__(self) -> None:
        self._email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        self._ip_pattern = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

    def sanitize_context(self, context: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        """Deep copy and sanitize context dictionary, removing internal keys and masking PII."""
        sanitized: dict[str, Any] = {}
        for key, val in context.items():
            if key.startswith("__") or key in ("secret", "password", "token", "private_key", "credentials"):
                sanitized[key] = "[REDACTED]"
            elif isinstance(val, str):
                sanitized[key] = self.mask_pii(val)
            elif isinstance(val, dict):
                sanitized[key] = self.sanitize_context(val, tenant_id=tenant_id)
            elif isinstance(val, list):
                sanitized[key] = [
                    self.sanitize_context(item, tenant_id=tenant_id) if isinstance(item, dict)
                    else (self.mask_pii(item) if isinstance(item, str) else item)
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
        masked = self._email_pattern.sub("[EMAIL_REDACTED]", text)
        masked = self._ip_pattern.sub("[IP_REDACTED]", masked)
        return masked

    def validate_tenant_access(
        self,
        requested_resource_tenant: str,
        current_tenant: str,
        is_admin: bool = False,
    ) -> bool:
        """Enforce strict multi-tenant boundary for resources and reservations."""
        if is_admin:
            return True
        if requested_resource_tenant.lower() == "system" or requested_resource_tenant.lower() == "global":
            return True
        return requested_resource_tenant.lower() == current_tenant.lower()


orchestration_privacy_manager = OrchestrationPrivacyManager()
