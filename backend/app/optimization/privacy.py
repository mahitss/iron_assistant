"""Privacy controls, multi-tenancy isolation, and data redaction for Optimization Engine (Task 62)."""

from __future__ import annotations

import re
from typing import Any

from app.optimization.safety import scrub_optimization_secrets


class OptimizationPrivacyManager:
    """Manages context sanitization, PII masking, and multi-tenant boundary enforcement for optimization data."""

    def __init__(self) -> None:
        self._email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        self._ip_pattern = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

    def sanitize_payload(self, payload: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        """Deep copy and sanitize payload, removing internal/secret keys and masking PII."""
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
                sanitized[key] = self.mask_pii(scrub_optimization_secrets(val))
            elif isinstance(val, dict):
                sanitized[key] = self.sanitize_payload(val, tenant_id=tenant_id)
            elif isinstance(val, list):
                sanitized[key] = [
                    self.sanitize_payload(item, tenant_id=tenant_id)
                    if isinstance(item, dict)
                    else (self.mask_pii(scrub_optimization_secrets(item)) if isinstance(item, str) else item)
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
        optimization_tenant: str,
        current_tenant: str,
        is_admin: bool = False,
    ) -> bool:
        """Enforce strict multi-tenant boundary for optimization history and experiments."""
        if is_admin or optimization_tenant.lower() in ("system", "global"):
            return True
        return optimization_tenant.lower() == current_tenant.lower()


optimization_privacy_manager = OptimizationPrivacyManager()
