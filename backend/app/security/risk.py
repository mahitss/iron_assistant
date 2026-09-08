"""Risk classification levels and deterministic risk assessment."""

from enum import Enum

from app.security.permissions import PermissionLevel


class RiskLevel(str, Enum):
    """Classification of risk and potential external side-effects."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Explicit risk mappings for registered and anticipated tools
TOOL_RISK_MAP: dict[str, RiskLevel] = {
    # Low risk (safe reads and queries)
    "calculator": RiskLevel.LOW,
    "datetime": RiskLevel.LOW,
    "system_info": RiskLevel.LOW,
    "web_search": RiskLevel.LOW,
    "web_fetch": RiskLevel.LOW,
    "browser_navigate": RiskLevel.LOW,
    "browser_inspect": RiskLevel.LOW,
    "browser_screenshot": RiskLevel.LOW,
    "computer_screenshot": RiskLevel.LOW,
    "computer_wait": RiskLevel.LOW,
    "computer_mouse_move": RiskLevel.LOW,
    "computer_mouse_scroll": RiskLevel.LOW,
    "git_status": RiskLevel.LOW,
    "git_branches": RiskLevel.LOW,
    "git_log": RiskLevel.LOW,
    "git_diff": RiskLevel.LOW,
    "code_search": RiskLevel.LOW,
    "code_read_file": RiskLevel.LOW,
    "code_analyze": RiskLevel.LOW,
    "github_list_repositories": RiskLevel.LOW,
    "github_get_repository": RiskLevel.LOW,
    "github_list_issues": RiskLevel.LOW,
    "github_get_issue": RiskLevel.LOW,
    "github_list_pull_requests": RiskLevel.LOW,
    "github_get_pull_request": RiskLevel.LOW,
    "github_get_pull_request_diff": RiskLevel.LOW,
    "github_get_checks": RiskLevel.LOW,
    # Medium risk (interactive user actions)
    "browser_click": RiskLevel.MEDIUM,
    # High risk (external execution, writes, simulated user inputs)
    "browser_fill": RiskLevel.HIGH,
    "computer_click": RiskLevel.HIGH,
    "computer_mouse_click": RiskLevel.HIGH,
    "computer_mouse_double_click": RiskLevel.HIGH,
    "computer_type": RiskLevel.HIGH,
    "computer_type_text": RiskLevel.HIGH,
    "computer_press_key": RiskLevel.HIGH,
    "test_runner": RiskLevel.HIGH,
    "git_commit": RiskLevel.HIGH,
    "git_push": RiskLevel.HIGH,
    "github_create_pr": RiskLevel.HIGH,
    # Critical risk (irreversible or destructive operations)
    "github_merge_pr": RiskLevel.CRITICAL,
    "system_shutdown": RiskLevel.CRITICAL,
}


def classify_risk(
    tool_name: str,
    permission_level: PermissionLevel | None = None,
    arguments: dict | None = None,
) -> RiskLevel:
    """Deterministically classify the risk level of an action.

    Priority:
    1. If permission is DESTRUCTIVE -> CRITICAL
    2. Explicit tool-level mapping in TOOL_RISK_MAP
    3. Permission fallback: WRITE/EXECUTE/EXTERNAL -> HIGH, READ -> LOW
    """
    if permission_level == PermissionLevel.DESTRUCTIVE:
        return RiskLevel.CRITICAL

    if tool_name in TOOL_RISK_MAP:
        return TOOL_RISK_MAP[tool_name]

    if permission_level in (PermissionLevel.WRITE, PermissionLevel.EXECUTE, PermissionLevel.EXTERNAL):
        return RiskLevel.HIGH

    return RiskLevel.LOW
