"""Permission definitions, capabilities taxonomy, and tool capability mappings."""

from enum import Enum


class PermissionLevel(str, Enum):
    """Classification of tool execution impact and privileges."""

    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    EXTERNAL = "EXTERNAL"
    DESTRUCTIVE = "DESTRUCTIVE"


class PermissionDecision(str, Enum):
    """Evaluation outcome for a tool execution request."""

    AUTO_ALLOWED = "AUTO_ALLOWED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    DENIED = "DENIED"


class Capability(str, Enum):
    """High-level user-controllable capability categories."""

    WEB_RESEARCH = "web_research"
    BROWSER = "browser"
    VOICE = "voice"
    VISION = "vision"
    COMPUTER_CONTROL = "computer_control"
    DEVELOPER_TOOLS = "developer_tools"
    AUTOMATION = "automation"


# Authoritative mapping of tools to their governing capability gate
TOOL_CAPABILITY_MAP: dict[str, Capability] = {
    # Web research tools
    "web_search": Capability.WEB_RESEARCH,
    "web_fetch": Capability.WEB_RESEARCH,
    # Browser tools
    "browser_navigate": Capability.BROWSER,
    "browser_inspect": Capability.BROWSER,
    "browser_screenshot": Capability.BROWSER,
    "browser_click": Capability.BROWSER,
    "browser_fill": Capability.BROWSER,
    # Developer & Git/GitHub tools
    "git_status": Capability.DEVELOPER_TOOLS,
    "git_branches": Capability.DEVELOPER_TOOLS,
    "git_log": Capability.DEVELOPER_TOOLS,
    "git_diff": Capability.DEVELOPER_TOOLS,
    "code_search": Capability.DEVELOPER_TOOLS,
    "code_read_file": Capability.DEVELOPER_TOOLS,
    "code_analyze": Capability.DEVELOPER_TOOLS,
    "github_list_repositories": Capability.DEVELOPER_TOOLS,
    "github_get_repository": Capability.DEVELOPER_TOOLS,
    "github_list_issues": Capability.DEVELOPER_TOOLS,
    "github_get_issue": Capability.DEVELOPER_TOOLS,
    "github_list_pull_requests": Capability.DEVELOPER_TOOLS,
    "github_get_pull_request": Capability.DEVELOPER_TOOLS,
    "github_get_pull_request_diff": Capability.DEVELOPER_TOOLS,
    "github_get_checks": Capability.DEVELOPER_TOOLS,
    "test_runner": Capability.DEVELOPER_TOOLS,
    "git_commit": Capability.DEVELOPER_TOOLS,
    "git_push": Capability.DEVELOPER_TOOLS,
    "github_create_pr": Capability.DEVELOPER_TOOLS,
    "github_merge_pr": Capability.DEVELOPER_TOOLS,
    # Computer control tools
    "computer_screenshot": Capability.COMPUTER_CONTROL,
    "computer_click": Capability.COMPUTER_CONTROL,
    "computer_type": Capability.COMPUTER_CONTROL,
    "computer_press_key": Capability.COMPUTER_CONTROL,
    "computer_mouse_move": Capability.COMPUTER_CONTROL,
    "computer_mouse_scroll": Capability.COMPUTER_CONTROL,
    "computer_wait": Capability.COMPUTER_CONTROL,
}


def get_tool_capability(tool_name: str) -> Capability | None:
    """Return the Capability category for a given tool name, or None if built-in."""
    return TOOL_CAPABILITY_MAP.get(tool_name)
