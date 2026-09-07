"""Tool registry for tool discovery, schema generation, and lifecycle management."""

from typing import Any, Dict, List, Optional
from app.tools.base import BaseTool
from app.tools.builtin.calculator import CalculatorTool
from app.tools.builtin.datetime import DateTimeTool
from app.tools.builtin.system_info import SystemInfoTool


class ToolRegistryError(Exception):
    """Base exception for tool registry operations."""
    pass


class DuplicateToolError(ToolRegistryError):
    """Raised when registering a tool with an existing name."""
    pass


class ToolRegistry:
    """Registry maintaining available tools and producing model-compatible schemas."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool, allow_override: bool = False) -> None:
        """Register a tool instance, preventing accidental duplicate names."""
        if tool.name in self._tools and not allow_override:
            raise DuplicateToolError(f"A tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check whether a tool with the given name exists."""
        return name in self._tools

    def list_tools(self) -> List[BaseTool]:
        """Return all currently registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI/OpenRouter-compatible function tool definitions for all registered tools."""
        return [tool.to_openrouter_schema() for tool in self._tools.values()]


def create_default_tool_registry() -> ToolRegistry:
    """Instantiate and register standard safe starter tools."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(SystemInfoTool())
    return registry
