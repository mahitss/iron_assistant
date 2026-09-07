"""Tests for ToolRegistry registration, lookups, and schema generation."""

from typing import Any
import pytest
from pydantic import BaseModel

from app.tools.base import BaseTool
from app.tools.permissions import PermissionLevel
from app.tools.registry import (
    DuplicateToolError,
    ToolRegistry,
    create_default_tool_registry,
)


class DummyArgs(BaseModel):
    query: str


class DummyTool(BaseTool):
    name = "dummy_tool"
    description = "A dummy tool for testing"
    permission_level = PermissionLevel.READ
    args_model = DummyArgs

    async def execute(self, query: str, **kwargs: Any) -> str:
        return f"processed {query}"


def test_tool_registry_registration_and_lookup() -> None:
    """Ensure tools can be registered and retrieved by name."""
    registry = ToolRegistry()
    tool = DummyTool()

    assert not registry.has_tool("dummy_tool")
    registry.register(tool)

    assert registry.has_tool("dummy_tool")
    assert registry.get("dummy_tool") == tool
    assert registry.get("nonexistent") is None


def test_tool_registry_duplicate_registration_handling() -> None:
    """Ensure duplicate tool names raise DuplicateToolError unless allowed."""
    registry = ToolRegistry()
    registry.register(DummyTool())

    with pytest.raises(DuplicateToolError):
        registry.register(DummyTool(), allow_override=False)

    # Overwrite allowed
    registry.register(DummyTool(), allow_override=True)
    assert len(registry.list_tools()) == 1


def test_tool_registry_listing_and_schemas() -> None:
    """Ensure registry lists tools and generates OpenAI/OpenRouter-compatible schemas."""
    registry = create_default_tool_registry()
    tools = registry.list_tools()

    tool_names = {t.name for t in tools}
    assert "calculator" in tool_names
    assert "datetime" in tool_names
    assert "system_info" in tool_names

    schemas = registry.get_schemas()
    assert len(schemas) == len(tools)
    calc_schema = next(s for s in schemas if s["function"]["name"] == "calculator")
    assert calc_schema["type"] == "function"
    assert "expression" in calc_schema["function"]["parameters"]["properties"]
