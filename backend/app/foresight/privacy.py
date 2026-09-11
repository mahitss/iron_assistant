"""Privacy, multi-tenant isolation, and PII masking for Autonomous World Model & Long-Horizon Foresight Engine (Task 65)."""

from __future__ import annotations

import re

from app.foresight.safety import ForesightSafetyError, scrub_foresight_secrets

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def mask_pii(text: str) -> str:
    """Mask personally identifiable information (emails, IPv4 addresses) in world observations."""
    if not text:
        return text
    masked = _EMAIL_PATTERN.sub("[MASKED_EMAIL]", text)
    masked = _IP_PATTERN.sub("[MASKED_IP]", masked)
    return masked


def validate_tenant_access(
    requested_tenant_id: str,
    resource_tenant_id: str,
    allow_system_override: bool = False,
) -> None:
    """Enforce strict multi-tenant boundary isolation (Spec 83).

    Entities, forecasts, and scenarios of one tenant can never be queried or modified by another.
    """
    if allow_system_override and requested_tenant_id in ("system", "admin", "superadmin"):
        return
    if requested_tenant_id != resource_tenant_id and resource_tenant_id != "default":
        raise ForesightSafetyError(
            f"Tenant Isolation Violation: Tenant '{requested_tenant_id}' cannot access world resource of tenant '{resource_tenant_id}'"
        )


def sanitize_and_mask_text(text: str) -> str:
    """Combined helper for PII masking and secret scrubbing."""
    return mask_pii(scrub_foresight_secrets(text))
