"""Data schemas for structured tool calls, tool invocations, and tool execution results."""

import json
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Structured tool invocation request produced by the model."""

    id: str = Field(..., description="Unique call identifier matching provider payload")
    name: str = Field(..., description="Target tool name to execute")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Parsed tool input arguments")

    model_config = {"frozen": True}


class ToolInvocation(BaseModel):
    """Typed invocation envelope for governed native and python tool execution."""

    invocation_id: str = Field(..., description="Unique invocation identifier")
    tool_name: str = Field(..., description="Name of the tool being executed")
    tool_version: str = Field(default="1.0.0", description="Semantic version of the target tool")
    capability_id: str | None = Field(default=None, description="Native runtime capability ID")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Validated input arguments")
    user_id: str = Field(default="default_user", description="Authenticated user ID")
    session_id: str | None = Field(default=None, description="Conversation or execution session ID")
    approval_id: str | None = Field(default=None, description="Bound approval ID if action required approval")
    deadline_ms: int | None = Field(default=30000, description="Hard deadline in milliseconds")
    cancellation_id: str | None = Field(default=None, description="Cancellation token ID")
    correlation_id: str | None = Field(default=None, description="Distributed correlation ID")


class ToolResult(BaseModel):
    """Structured result returned after tool execution."""

    success: bool = Field(..., description="True if the tool executed without error")
    tool_name: str = Field(..., description="Name of the executed tool")
    tool_call_id: str | None = Field(default=None, description="Matching ToolCall ID")
    result: Any | None = Field(default=None, description="Output returned by the tool")
    error: str | None = Field(default=None, description="Clean error message if execution failed")
    verification_status: str = Field(
        default="verified", description="Outcome of output verification (verified/failed/skipped/denied)"
    )
    approval_required: bool = Field(
        default=False, description="True if action was halted pending user approval"
    )
    execution_class: str | None = Field(
        default=None, description="Execution classification (PYTHON, NATIVE_RUST, REMOTE, COMPOSITE)"
    )
    capability_id: str | None = Field(
        default=None, description="Native runtime capability ID if executed natively"
    )
    duration_ms: float | None = Field(
        default=None, description="Execution duration in milliseconds"
    )
    resource_telemetry: dict[str, Any] | None = Field(
        default=None, description="Measured resource usage telemetry from runtime"
    )
    provenance: dict[str, Any] | None = Field(
        default=None, description="Execution provenance (tool version, runtime version, invocation id, etc.)"
    )

    def to_model_output(self) -> str:
        """Format the result as a clean JSON string for LLM tool message consumption."""
        if self.approval_required:
            return json.dumps(
                {
                    "status": "approval_required",
                    "tool": self.tool_name,
                    "approval_required": True,
                    "message": self.error
                    or f"Action '{self.tool_name}' requires explicit user approval before execution.",
                }
            )
        if not self.success:
            return json.dumps({"status": "error", "tool": self.tool_name, "error": self.error})
        return json.dumps({"status": "success", "tool": self.tool_name, "result": self.result})
