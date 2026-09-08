"""Data schemas for structured tool calls and tool execution results."""

import json
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Structured tool invocation request produced by the model."""

    id: str = Field(..., description="Unique call identifier matching provider payload")
    name: str = Field(..., description="Target tool name to execute")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Parsed tool input arguments")

    model_config = {"frozen": True}


class ToolResult(BaseModel):
    """Structured result returned after tool execution."""

    success: bool = Field(..., description="True if the tool executed without error")
    tool_name: str = Field(..., description="Name of the executed tool")
    tool_call_id: str | None = Field(default=None, description="Matching ToolCall ID")
    result: Any | None = Field(default=None, description="Output returned by the tool")
    error: str | None = Field(default=None, description="Clean error message if execution failed")
    verification_status: str = Field(default="verified", description="Outcome of output verification (verified/failed/skipped)")

    def to_model_output(self) -> str:
        """Format the result as a clean JSON string for LLM tool message consumption."""
        if not self.success:
            return json.dumps({"status": "error", "tool": self.tool_name, "error": self.error})
        return json.dumps({"status": "success", "tool": self.tool_name, "result": self.result})
