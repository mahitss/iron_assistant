"""Domain ownership matrix and boundary enforcement (Task 39, Spec 8, 42-49)."""

import logging
from typing import Any

from app.state.schemas import StateClassification, StateDomain

logger = logging.getLogger("kairo.state.ownership")

# Map each domain to its authorized service identifiers
_DOMAIN_AUTHORIZED_SERVICES: dict[StateDomain, set[str]] = {
    StateDomain.TASKS: {"task_engine", "tasks", "task_service", "system"},
    StateDomain.APPROVALS: {"approval_service", "approvals", "security", "system"},
    StateDomain.POLICIES: {"policy_engine", "governance", "security", "system"},
    StateDomain.IDENTITY: {"identity_service", "identity", "auth", "system"},
    StateDomain.DEVICES: {"device_service", "devices", "identity", "security", "system"},
    StateDomain.PROJECTS: {"project_service", "projects", "system"},
    StateDomain.NOTIFICATIONS: {"notification_service", "notifications", "system"},
    StateDomain.MEMORY: {"memory_service", "memory", "system"},
    StateDomain.WORLD: {"world_model", "world", "system"},
    StateDomain.AUDIT: {"audit_service", "audit", "security", "system"},
}


class DomainOwnershipRegistry:
    """Enforces strict domain ownership boundaries for authoritative mutations."""

    @classmethod
    def is_service_authorized(cls, domain: StateDomain, service_name: str) -> bool:
        """Check if service is authorized to mutate authoritative domain state."""
        authorized = _DOMAIN_AUTHORIZED_SERVICES.get(domain, {"system"})
        return service_name.lower() in authorized

    @classmethod
    def validate_mutation_authority(
        cls,
        domain: StateDomain,
        service_name: str,
        classification: StateClassification = StateClassification.AUTHORITATIVE,
    ) -> None:
        """Validates mutation permission.
        
        Invariant: Only the owning subsystem may mutate authoritative state.
        Derived state can be updated by its projection builder.
        """
        if classification != StateClassification.AUTHORITATIVE:
            return

        if not cls.is_service_authorized(domain, service_name):
            logger.warning(
                "Unauthorized mutation attempt on domain '%s' by service '%s'",
                domain.value,
                service_name,
            )
            raise PermissionError(
                f"Unauthorized mutation: Service '{service_name}' is not authorized to mutate authoritative state for domain '{domain.value}'"
            )

    @classmethod
    def validate_security_scope(
        cls,
        record_user_id: str | None,
        request_user_id: str | None,
        record_project_id: str | None,
        request_project_id: str | None,
        allow_cross_project: bool = False,
    ) -> None:
        """Validates user and project boundaries (Specs 47-49).
        
        Default: Cross-user mutation/read is strictly DENIED.
        Default: Cross-project mutation/read is strictly DENIED.
        """
        # 1. User isolation
        if record_user_id and request_user_id:
            if record_user_id != request_user_id:
                raise PermissionError(
                    f"Cross-user state access denied: user '{request_user_id}' cannot access records owned by '{record_user_id}'"
                )

        # 2. Project isolation
        if record_project_id and request_project_id and not allow_cross_project:
            if record_project_id != request_project_id:
                raise PermissionError(
                    f"Cross-project state access denied: project '{request_project_id}' cannot access records owned by '{record_project_id}'"
                )
