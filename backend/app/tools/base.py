"""Base abstractions and contracts for Kairo tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel, Field

from app.tools.permissions import PermissionLevel


class ToolDefinition(BaseModel):
    """Metadata describing a tool and its input schema."""

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Detailed description of tool functionality")
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.READ,
        description="Required permission level for execution",
    )
    parameters_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="OpenAPI/JSON Schema for tool arguments",
    )

    model_config = {"frozen": True}


class BaseTool(ABC):
    """Abstract base class for all Kairo tools."""

    name: str
    description: str
    permission_level: PermissionLevel = PermissionLevel.READ
    args_model: Type[BaseModel]

    @property
    def definition(self) -> ToolDefinition:
        """Generate ToolDefinition from class attributes and Pydantic schema."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            permission_level=self.permission_level,
            parameters_schema=self.get_parameters_schema(),
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Extract JSON Schema from the tool's Pydantic arguments model."""
        schema = self.args_model.model_json_schema()
        # Clean up unwanted metadata fields if present
        schema.pop("title", None)
        return schema

    def to_openrouter_schema(self) -> Dict[str, Any]:
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
