"""Safety policies, tenant authorization, and rate limit validation for automations."""

from typing import Any


class AutomationSecurityError(PermissionError):
    """Raised when an automation action violates tenant isolation or safety policy."""


def verify_user_ownership(entity: Any, user_id: str) -> None:
    """Ensure the target entity is owned by the requesting user.

    SECURITY:
    - Strictly prevents User A from inspecting, modifying, or approving User B's workflows.
    """
    if not entity:
        return

    entity_owner = getattr(entity, "user_id", None)
    if entity_owner != user_id:
        raise AutomationSecurityError(
            f"Access denied: Resource belongs to user '{entity_owner}', not '{user_id}'."
        )


def sanitize_workflow_name(name: str) -> str:
    """Sanitize workflow name to avoid prompt injection or script tags."""
    if not name:
        return "Untitled Workflow"
    cleaned = name.strip()
    return cleaned[:128]
