"""Approval management for human-in-the-loop workflow gating."""

import logging
from datetime import UTC, datetime, timedelta

from app.automation.models import ApprovalRequest

logger = logging.getLogger("kairo.automation.approvals")


class ApprovalExpiredError(RuntimeError):
    """Raised when an approval request has expired."""


class ApprovalAlreadyDecidedError(RuntimeError):
    """Raised when attempting to decide an already approved or denied request."""


def create_approval_request(
    user_id: str,
    run_id: str,
    tool_name: str,
    tool_args: dict,
    permission_level: str,
    step_id: str | None = None,
    timeout_seconds: int = 30,
) -> ApprovalRequest:
    """Create a new pending ApprovalRequest with expiration."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=max(5, timeout_seconds))
    return ApprovalRequest(
        user_id=user_id,
        run_id=run_id,
        step_id=step_id,
        tool_name=tool_name,
        tool_args=tool_args,
        permission_level=permission_level,
        status="pending",
        created_at=now,
        expires_at=expires_at,
    )


def is_approval_expired(approval: ApprovalRequest) -> bool:
    """Check if approval has passed its expires_at deadline."""
    if approval.status != "pending":
        return False
    return datetime.now(UTC) > approval.expires_at


def apply_approval_decision(
    approval: ApprovalRequest,
    decision: str,  # "approve" | "deny"
    user_id: str,
) -> ApprovalRequest:
    """Apply an approval decision enforcing expiration and status rules."""
    if approval.user_id != user_id:
        raise PermissionError(f"User '{user_id}' cannot decide approval for user '{approval.user_id}'.")

    if approval.status != "pending":
        raise ApprovalAlreadyDecidedError(f"Approval request '{approval.id}' is already {approval.status}.")

    if is_approval_expired(approval):
        approval.status = "expired"
        approval.decided_at = datetime.now(UTC)
        raise ApprovalExpiredError(f"Approval request '{approval.id}' has expired.")

    now = datetime.now(UTC)
    if decision == "approve":
        approval.status = "approved"
    elif decision == "deny":
        approval.status = "denied"
    else:
        raise ValueError(f"Invalid decision '{decision}'. Expected 'approve' or 'deny'.")

    approval.decided_at = now
    return approval
