"""Tool registry for tool discovery, schema generation, and lifecycle management."""

from typing import Any

from app.tools.base import BaseTool
from app.tools.builtin.calculator import CalculatorTool
from app.tools.builtin.datetime import DateTimeTool
from app.tools.builtin.system_info import SystemInfoTool


class ToolRegistryError(Exception):
    """Base exception for tool registry operations."""


class DuplicateToolError(ToolRegistryError):
    """Raised when registering a tool with an existing name."""


class ToolRegistry:
    """Registry maintaining available tools and producing model-compatible schemas."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool, allow_override: bool = False) -> None:
        """Register a tool instance, preventing accidental duplicate names."""
        if tool.name in self._tools and not allow_override:
            raise DuplicateToolError(f"A tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check whether a tool with the given name exists."""
        return name in self._tools

    def list_tools(self) -> list[BaseTool]:
        """Return all currently registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI/OpenRouter-compatible function tool definitions for all registered tools."""
        return [tool.to_openrouter_schema() for tool in self._tools.values()]


def create_default_tool_registry() -> ToolRegistry:
    """Instantiate and register standard safe starter tools, web research tools, and browser tools."""
    from app.core.config import get_settings
    from app.tools.web.fetch import WebFetchTool
    from app.tools.web.search import WebSearchTool

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(SystemInfoTool())
    registry.register(WebSearchTool())
    registry.register(WebFetchTool())

    if get_settings().KAIRO_BROWSER_ENABLED:
        from app.tools.browser.actions import (
            BrowserClickTool,
            BrowserFillTool,
            BrowserInspectTool,
            BrowserNavigateTool,
            BrowserScreenshotTool,
        )

        registry.register(BrowserNavigateTool())
        registry.register(BrowserInspectTool())
        registry.register(BrowserScreenshotTool())
        registry.register(BrowserClickTool())
        registry.register(BrowserFillTool())

    if get_settings().KAIRO_DEVELOPER_ENABLED:
        from app.tools.builtin.developer import (
            CodeAnalysisTool,
            CodeReadFileTool,
            CodeSearchTool,
            GitBranchesTool,
            GitDiffTool,
            GitHubGetChecksTool,
            GitHubGetIssueTool,
            GitHubGetPullRequestDiffTool,
            GitHubGetPullRequestTool,
            GitHubGetRepositoryTool,
            GitHubListIssuesTool,
            GitHubListPullRequestsTool,
            GitHubListRepositoriesTool,
            GitLogTool,
            GitStatusTool,
            TestRunnerTool,
        )

        registry.register(GitStatusTool())
        registry.register(GitBranchesTool())
        registry.register(GitLogTool())
        registry.register(GitDiffTool())
        registry.register(CodeSearchTool())
        registry.register(CodeReadFileTool())
        registry.register(CodeAnalysisTool())
        registry.register(GitHubListRepositoriesTool())
        registry.register(GitHubGetRepositoryTool())
        registry.register(GitHubListIssuesTool())
        registry.register(GitHubGetIssueTool())
        registry.register(GitHubListPullRequestsTool())
        registry.register(GitHubGetPullRequestTool())
        registry.register(GitHubGetPullRequestDiffTool())
        registry.register(GitHubGetChecksTool())
        registry.register(TestRunnerTool())

    return registry

