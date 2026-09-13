"""Base abstractions and contracts for Kairo tools."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.tools.permissions import PermissionLevel


class ToolExecutionClass(str, Enum):
    """Classification of tool execution runtime."""

    PYTHON = "PYTHON"
    NATIVE_RUST = "NATIVE_RUST"
    REMOTE = "REMOTE"
    COMPOSITE = "COMPOSITE"


class ToolExecutionPreference(str, Enum):
    """Routing preference when multiple execution environments exist."""

    NATIVE_REQUIRED = "NATIVE_REQUIRED"
    NATIVE_PREFERRED = "NATIVE_PREFERRED"
    PYTHON_PREFERRED = "PYTHON_PREFERRED"
    PYTHON_REQUIRED = "PYTHON_REQUIRED"


class ToolAvailability(str, Enum):
    """Operational readiness state of a tool."""

    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"
    INCOMPATIBLE = "INCOMPATIBLE"


class ToolDefinition(BaseModel):
    """Metadata describing a tool and its execution contract."""

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Detailed description of tool functionality")
    version: str = Field(default="1.0.0", description="Semantic version of the tool contract")
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.READ,
        description="Required permission level for execution",
    )
    execution_class: ToolExecutionClass = Field(
        default=ToolExecutionClass.PYTHON,
        description="Execution substrate (PYTHON, NATIVE_RUST, REMOTE, COMPOSITE)",
    )
    preference: ToolExecutionPreference = Field(
        default=ToolExecutionPreference.PYTHON_PREFERRED,
        description="Substrate routing preference",
    )
    capability_id: Optional[str] = Field(
        default=None,
        description="Underlying low-level native runtime capability ID",
    )
    sandbox_profile: str = Field(
        default="STANDARD",
        description="Target sandbox profile (MINIMAL, STANDARD, STRICT)",
    )
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="OpenAPI/JSON Schema for tool arguments",
    )
    output_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="OpenAPI/JSON Schema for structured tool outputs",
    )
    timeout_seconds: float = Field(
        default=30.0,
        description="Execution timeout bound in seconds",
    )
    idempotent: bool = Field(
        default=True,
        description="Whether the tool operation is safe to retry without compounding side effects",
    )
    fallback_tool: Optional[str] = Field(
        default=None,
        description="Name of safe fallback tool if native execution is degraded",
    )

    model_config = {"frozen": True}


class BaseTool(ABC):
    """Abstract base class for all Kairo tools."""

    name: str
    description: str
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.READ
    execution_class: ToolExecutionClass = ToolExecutionClass.PYTHON
    preference: ToolExecutionPreference = ToolExecutionPreference.PYTHON_PREFERRED
    capability_id: Optional[str] = None
    sandbox_profile: str = "STANDARD"
    args_model: type[BaseModel]
    output_model: Optional[type[BaseModel]] = None
    timeout_seconds: float = 30.0
    idempotent: bool = True
    fallback_tool: Optional[str] = None

    @property
    def definition(self) -> ToolDefinition:
        """Generate ToolDefinition from class attributes and Pydantic schemas."""
        out_schema = None
        if self.output_model is not None:
            out_schema = self.output_model.model_json_schema()
            out_schema.pop("title", None)

        return ToolDefinition(
            name=self.name,
            description=self.description,
            version=self.version,
            permission_level=self.permission_level,
            execution_class=self.execution_class,
            preference=self.preference,
            capability_id=self.capability_id,
            sandbox_profile=self.sandbox_profile,
            parameters_schema=self.get_parameters_schema(),
            output_schema=out_schema,
            timeout_seconds=self.timeout_seconds,
            idempotent=self.idempotent,
            fallback_tool=self.fallback_tool,
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        """Extract JSON Schema from the tool's Pydantic arguments model."""
        schema = self.args_model.model_json_schema()
        schema.pop("title", None)
        return schema

    def to_openrouter_schema(self) -> dict[str, Any]:
        """Format the tool as an OpenAI/OpenRouter-compatible function tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema(),
            },
        }

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool logic with validated keyword arguments."""
        ...

    def verify(self, result: Any) -> bool:
        """Optional post-execution verification hook. Default implementation accepts valid results."""
        return True
