"""Privacy, multi-tenant isolation, and mission data boundary enforcement (Task 66)."""

from __future__ import annotations

import logging
from typing import Any

from app.missions.safety import MissionSafetyError

logger = logging.getLogger("kairo.missions.privacy")


def validate_mission_tenant(
    expected_tenant: str,
    requested_tenant: str,
    mission_id: str,
) -> None:
    """Enforce strict multi-tenant boundary isolation across missions (Spec 87, 89).

    Invariant: Different missions must never leak private context, credentials, or state.
    """
    if expected_tenant != requested_tenant:
        logger.warning(
            "TENANT_ISOLATION_VIOLATION: Mission %s belongs to tenant '%s', access attempted by '%s'",
            mission_id,
            expected_tenant,
            requested_tenant,
        )
        raise MissionSafetyError(
            f"Tenant Isolation Violation: Access to mission '{mission_id}' denied for tenant '{requested_tenant}'."
        )


def sanitize_mission_context(context: dict[str, Any]) -> dict[str, Any]:
    """Strip out unneeded PII and isolate context data to necessary fields only (Spec 87)."""
    if not isinstance(context, dict):
        return {}

    sanitized: dict[str, Any] = {}
    sensitive_keys = {"ssn", "password", "secret", "private_key", "token", "credit_card"}

    for k, v in context.items():
        if k.lower() in sensitive_keys:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_mission_context(v)
        else:
            sanitized[k] = v

    return sanitized
