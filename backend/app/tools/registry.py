"""Tool registry for tool discovery, schema generation, lifecycle management, and native tool execution fabric."""

from collections import deque
from typing import Any

from app.tools.base import (
    BaseTool,
    ToolAvailability,
    ToolExecutionClass,
    ToolExecutionPreference,
)
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
        # Metrics per tool: invocations, successes, failures, timeouts, resource_violations, fallbacks, recent latencies
        self._metrics: dict[str, dict[str, Any]] = {}

    def register(self, tool: BaseTool, allow_override: bool = False) -> None:
        """Register a tool instance, preventing accidental duplicate names."""
        if tool.name in self._tools and not allow_override:
            raise DuplicateToolError(f"A tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool
        if tool.name not in self._metrics:
            self._metrics[tool.name] = {
                "invocations": 0,
                "successes": 0,
                "failures": 0,
                "timeouts": 0,
                "resource_violations": 0,
                "fallbacks": 0,
                "recent_latencies_ms": deque(maxlen=50),
            }

    def get(self, name: str) -> BaseTool | None:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check whether a tool with the given name exists."""
        return name in self._tools

    def list_tools(self) -> list[BaseTool]:
        """Return all currently registered tools."""
        return list(self._tools.values())

    def list_native_tools(self) -> list[BaseTool]:
        """Return all tools that support or require native execution."""
        return [
            tool
            for tool in self._tools.values()
            if tool.execution_class == ToolExecutionClass.NATIVE_RUST or tool.capability_id is not None
        ]

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI/OpenRouter-compatible function tool definitions for all registered tools."""
        return [tool.to_openrouter_schema() for tool in self._tools.values()]

    def record_invocation(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        is_timeout: bool = False,
        is_resource_violation: bool = False,
        is_fallback: bool = False,
    ) -> None:
        """Record execution metrics for observability and reliability modeling."""
        if tool_name not in self._metrics:
            self._metrics[tool_name] = {
                "invocations": 0,
                "successes": 0,
                "failures": 0,
                "timeouts": 0,
                "resource_violations": 0,
                "fallbacks": 0,
                "recent_latencies_ms": deque(maxlen=50),
            }
        m = self._metrics[tool_name]
        m["invocations"] += 1
        if success:
            m["successes"] += 1
        else:
            m["failures"] += 1
        if is_timeout:
            m["timeouts"] += 1
        if is_resource_violation:
            m["resource_violations"] += 1
        if is_fallback:
            m["fallbacks"] += 1
        m["recent_latencies_ms"].append(duration_ms)

    def get_tool_metrics(self, tool_name: str | None = None) -> dict[str, Any]:
        """Return summary health and reliability statistics by tool."""
        if tool_name:
            m = self._metrics.get(tool_name)
            if not m:
                return {
                    "tool": tool_name,
                    "invocations": 0,
                    "success_rate": 1.0,
                    "avg_latency_ms": 0.0,
                    "failures": 0,
                    "timeouts": 0,
                    "resource_violations": 0,
                    "fallbacks": 0,
                }
            inv = m["invocations"]
            succ = m["successes"]
            latencies = list(m["recent_latencies_ms"])
            avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
            return {
                "tool": tool_name,
                "invocations": inv,
                "successes": succ,
                "success_rate": (succ / inv) if inv > 0 else 1.0,
                "avg_latency_ms": round(avg_lat, 2),
                "failures": m["failures"],
                "timeouts": m["timeouts"],
                "resource_violations": m["resource_violations"],
                "fallbacks": m["fallbacks"],
            }

        result = {}
        for name in self._tools.keys():
            result[name] = self.get_tool_metrics(name)
        return result

    def get_tool_status(
        self,
        name: str,
        runtime_healthy: bool | None = None,
        runtime_mode: str = "OPTIONAL",
    ) -> ToolAvailability:
        """Determine operational readiness state of a tool."""
        tool = self.get(name)
        if tool is None:
            return ToolAvailability.UNAVAILABLE

        if tool.execution_class == ToolExecutionClass.PYTHON:
            return ToolAvailability.AVAILABLE

        # Native tool
        if runtime_mode == "DISABLED":
            if tool.preference == ToolExecutionPreference.NATIVE_REQUIRED:
                return ToolAvailability.DISABLED
            return ToolAvailability.DEGRADED

        if runtime_healthy is False:
            if tool.preference == ToolExecutionPreference.NATIVE_REQUIRED:
                return ToolAvailability.UNAVAILABLE
            return ToolAvailability.DEGRADED

        return ToolAvailability.AVAILABLE

    def get_native_tool_catalog(
        self,
        runtime_healthy: bool = True,
        runtime_mode: str = "OPTIONAL",
    ) -> list[dict[str, Any]]:
        """Return full catalog of tools with execution and availability metadata."""
        catalog = []
        for tool in self._tools.values():
            defn = tool.definition
            status = self.get_tool_status(tool.name, runtime_healthy, runtime_mode)
            metrics = self.get_tool_metrics(tool.name)
            catalog.append({
                "name": defn.name,
                "description": defn.description,
                "version": defn.version,
                "permission_level": defn.permission_level.value,
                "execution_class": defn.execution_class.value,
                "preference": defn.preference.value,
                "capability_id": defn.capability_id,
                "sandbox_profile": defn.sandbox_profile,
                "availability": status.value,
                "timeout_seconds": defn.timeout_seconds,
                "idempotent": defn.idempotent,
                "fallback_tool": defn.fallback_tool,
                "parameters_schema": defn.parameters_schema,
                "output_schema": defn.output_schema,
                "metrics": metrics,
            })
        return catalog


def create_default_tool_registry() -> ToolRegistry:
    """Instantiate and register standard starter tools, native tools, web research tools, and browser tools."""
    from app.core.config import get_settings
    from app.tools.builtin.native import (
        NativeHashTool,
        NativeProbeTool,
        NativeSystemInfoTool,
        NativeWorkspaceInspectTool,
    )
    from app.tools.web.fetch import WebFetchTool
    from app.tools.web.search import WebSearchTool

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(SystemInfoTool())
    registry.register(WebSearchTool())
    registry.register(WebFetchTool())

    # Register Native Rust-backed tools (Task 83)
    registry.register(NativeHashTool())
    registry.register(NativeSystemInfoTool())
    registry.register(NativeWorkspaceInspectTool())
    registry.register(NativeProbeTool())

    # Register Native Computer Interaction Substrate Tools (Task 84)
    from app.tools.builtin.computer import (
        NativeClipboardReadTool,
        NativeClipboardWriteTool,
        NativeDisplayInspectTool,
        NativeKeyboardActionTool,
        NativeMouseActionTool,
        NativeProcessInspectTool,
        NativeScreenCaptureTool,
        NativeWindowInspectTool,
    )
    registry.register(NativeWindowInspectTool())
    registry.register(NativeProcessInspectTool())
    registry.register(NativeDisplayInspectTool())
    registry.register(NativeScreenCaptureTool())
    registry.register(NativeClipboardReadTool())
    registry.register(NativeClipboardWriteTool())
    registry.register(NativeMouseActionTool())
    registry.register(NativeKeyboardActionTool())

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
