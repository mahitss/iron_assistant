"""Privacy, multi-tenant isolation, and data boundary enforcement for Self-Audit Engine (Task 67)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kairo.self_audit.privacy")


class TenantIsolationError(Exception):
    """Raised when cross-tenant access to private audit records is attempted (Spec 68, 85)."""


def validate_audit_tenant(resource_tenant_id: str, requesting_tenant_id: str, resource_id: str) -> None:
    """Enforce strict multi-tenant scoping across self-audit telemetry, beliefs, and records."""
    if resource_tenant_id != requesting_tenant_id:
        logger.warning(
            "CROSS_TENANT_VIOLATION_BLOCKED: resource=%s owner_tenant=%s requester_tenant=%s",
            resource_id,
            resource_tenant_id,
            requesting_tenant_id,
        )
        raise TenantIsolationError(
            f"Tenant Isolation Violation: Requester '{requesting_tenant_id}' cannot access "
            f"self-audit resource '{resource_id}' belonging to '{resource_tenant_id}'."
        )


def redact_tenant_private_telemetry(data: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """Ensure sensitive payload data is minimized and stripped of foreign tenant identifiers."""
    cleaned = dict(data)
    cleaned["tenant_id"] = tenant_id
    if "raw_memory_dumps" in cleaned:
        cleaned.pop("raw_memory_dumps", None)
    return cleaned
