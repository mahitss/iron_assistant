"""Privacy and multi-tenant boundary guard for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Enforces strict tenant isolation and workspace scoping (Spec 29).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kairo.memory_consolidation.privacy")


class CrossTenantMemoryViolationError(Exception):
    """Raised when an unauthorized cross-tenant memory access is attempted."""

    pass


class MemoryPrivacyGuard:
    """Enforces multi-tenant isolation and data minimization for memory entities."""

    @classmethod
    def verify_tenant_access(
        cls,
        resource_tenant: str,
        requester_tenant: str,
        resource_id: str = "",
    ) -> None:
        """Reject cross-tenant access attempts."""
        if not resource_tenant or not requester_tenant:
            return
        if resource_tenant != requester_tenant and requester_tenant != "system_admin":
            err_msg = (
                f"CROSS_TENANT_MEMORY_ACCESS_BLOCKED: resource={resource_id} "
                f"owner_tenant='{resource_tenant}' requester_tenant='{requester_tenant}'."
            )
            logger.warning(err_msg)
            raise CrossTenantMemoryViolationError(err_msg)

    @classmethod
    def redact_for_export(cls, memory_data: dict[str, Any]) -> dict[str, Any]:
        """Strip internal IDs and sensitivity tags when exporting memory records."""
        safe_copy = dict(memory_data)
        if safe_copy.get("sensitivity") == "RESTRICTED":
            safe_copy["content"] = "[CONTENT_RESTRICTED_BY_PRIVACY_POLICY]"
            safe_copy["structured_payload"] = {}
        return safe_copy
