"""Centralized security policy matrix and decision rules."""

from enum import Enum

from app.security.permissions import PermissionLevel
from app.security.risk import RiskLevel, classify_risk


class SecurityDecision(str, Enum):
    """Authoritative decision on a tool execution request."""

    ALLOWED = "ALLOWED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    DENIED = "DENIED"


# Explicit tool-level policy overrides
# (Default decision before user approval check)
TOOL_POLICY_OVERRIDES: dict[str, SecurityDecision] = {
    # Safe read tools
    "calculator": SecurityDecision.ALLOWED,
    "datetime": SecurityDecision.ALLOWED,
    "system_info": SecurityDecision.ALLOWED,
    "web_search": SecurityDecision.ALLOWED,
    "web_fetch": SecurityDecision.ALLOWED,
    "browser_navigate": SecurityDecision.ALLOWED,
    "browser_inspect": SecurityDecision.ALLOWED,
    "browser_screenshot": SecurityDecision.ALLOWED,
    "computer_screenshot": SecurityDecision.ALLOWED,
    "computer_wait": SecurityDecision.ALLOWED,
    "git_status": SecurityDecision.ALLOWED,
    "git_branches": SecurityDecision.ALLOWED,
    "git_log": SecurityDecision.ALLOWED,
    "git_diff": SecurityDecision.ALLOWED,
    "code_search": SecurityDecision.ALLOWED,
    "code_read_file": SecurityDecision.ALLOWED,
    "code_analyze": SecurityDecision.ALLOWED,
    "github_list_repositories": SecurityDecision.ALLOWED,
    "github_get_repository": SecurityDecision.ALLOWED,
    "github_list_issues": SecurityDecision.ALLOWED,
    "github_get_issue": SecurityDecision.ALLOWED,
    "github_list_pull_requests": SecurityDecision.ALLOWED,
    "github_get_pull_request": SecurityDecision.ALLOWED,
    "github_get_pull_request_diff": SecurityDecision.ALLOWED,
    "github_get_checks": SecurityDecision.ALLOWED,
    # Interactive / External actions requiring approval
    "browser_click": SecurityDecision.APPROVAL_REQUIRED,
    "browser_fill": SecurityDecision.APPROVAL_REQUIRED,
    "computer_click": SecurityDecision.APPROVAL_REQUIRED,
    "computer_mouse_click": SecurityDecision.APPROVAL_REQUIRED,
    "computer_mouse_double_click": SecurityDecision.APPROVAL_REQUIRED,
    "computer_type": SecurityDecision.APPROVAL_REQUIRED,
    "computer_type_text": SecurityDecision.APPROVAL_REQUIRED,
    "computer_press_key": SecurityDecision.APPROVAL_REQUIRED,
    "test_runner": SecurityDecision.APPROVAL_REQUIRED,
    "git_commit": SecurityDecision.APPROVAL_REQUIRED,
    "git_push": SecurityDecision.APPROVAL_REQUIRED,
    "github_create_pr": SecurityDecision.APPROVAL_REQUIRED,
    # Destructive operations strictly denied
    "github_merge_pr": SecurityDecision.DENIED,
    "system_shutdown": SecurityDecision.DENIED,
}


def evaluate_tool_policy(
    tool_name: str,
    permission_level: PermissionLevel | None = None,
    arguments: dict | None = None,
) -> tuple[SecurityDecision, RiskLevel]:
    """Evaluate central security policy matrix for a requested tool action."""
    risk = classify_risk(tool_name, permission_level, arguments)

    # 1. Immediate denial for DESTRUCTIVE or CRITICAL
    if permission_level == PermissionLevel.DESTRUCTIVE or risk == RiskLevel.CRITICAL:
        return SecurityDecision.DENIED, RiskLevel.CRITICAL

    # 2. Check explicit tool override table
    if tool_name in TOOL_POLICY_OVERRIDES:
        return TOOL_POLICY_OVERRIDES[tool_name], risk

    # 3. Fallback based on permission level
    if permission_level == PermissionLevel.READ:
        return SecurityDecision.ALLOWED, RiskLevel.LOW
    elif permission_level in (PermissionLevel.WRITE, PermissionLevel.EXTERNAL, PermissionLevel.EXECUTE):
        return SecurityDecision.APPROVAL_REQUIRED, RiskLevel.HIGH

    return SecurityDecision.DENIED, RiskLevel.HIGH
