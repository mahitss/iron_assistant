"""Model capabilities, definitions, and registry for Kairo."""

from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, field_validator


class ModelCapability(str, Enum):
    """Supported model capabilities for intelligent task routing."""

    GENERAL = "general"
    REASONING = "reasoning"
    CODING = "coding"
    VISION = "vision"
    FAST = "fast"
    TOOL_CALLING = "tool_calling"
    STRUCTURED_OUTPUT = "structured_output"

    @classmethod
    def from_str(cls, value: Union[str, "ModelCapability"]) -> "ModelCapability":
        """Convert string to ModelCapability safely."""
        if isinstance(value, ModelCapability):
            return value
        try:
            return cls(value.strip().lower())
        except (ValueError, AttributeError):
            valid = [c.value for c in cls]
            raise ValueError(f"Unknown capability '{value}'. Valid capabilities are: {', '.join(valid)}")


class ModelDefinition(BaseModel):
    """Typed definition representing a configured AI model."""

    id: str = Field(..., min_length=1, description="Unique model identifier or router target")
    provider: str = Field(default="openrouter", description="Upstream provider identifier")
    capabilities: set[ModelCapability] = Field(
        default_factory=lambda: {ModelCapability.GENERAL},
        description="Set of capabilities this model provides",
    )
    priority: int = Field(
        default=0,
        description="Selection priority (higher values take precedence for matched capabilities)",
    )
    enabled: bool = Field(default=True, description="Whether the model is active and available for routing")
    description: str | None = Field(default=None, description="Optional description of the model")

    @field_validator("capabilities", mode="before")
    @classmethod
    def parse_capabilities(cls, v: set[str | ModelCapability] | list[str | ModelCapability]) -> set[ModelCapability]:
        """Normalize capability strings into ModelCapability enums."""
        result = set()
        for item in v:
            result.add(ModelCapability.from_str(item))
        return result

    model_config = {"frozen": True}


class ModelRegistryError(Exception):
    """Base exception for model registry operations."""


class DuplicateModelError(ModelRegistryError):
    """Raised when registering a model ID that already exists."""


class ModelNotFoundError(ModelRegistryError):
    """Raised when looking up an unregistered model ID."""


class ModelRegistry:
    """Registry maintaining configured models, metadata, and capability indexing."""

    def __init__(self) -> None:
        self._models: dict[str, ModelDefinition] = {}

    def register_model(self, model: ModelDefinition, allow_override: bool = False) -> None:
        """Register a model definition in the registry."""
        if model.id in self._models and not allow_override:
            raise DuplicateModelError(f"Model with ID '{model.id}' is already registered.")
        self._models[model.id] = model

    def get_model(self, model_id: str) -> ModelDefinition | None:
        """Retrieve a model by its identifier."""
        return self._models.get(model_id)

    def list_models(self, enabled_only: bool = True) -> list[ModelDefinition]:
        """List registered models, optionally filtering by enabled status."""
        models = list(self._models.values())
        if enabled_only:
            return [m for m in models if m.enabled]
        return models

    def get_models_for_capability(
        self,
        capability: ModelCapability | str,
        enabled_only: bool = True,
    ) -> list[ModelDefinition]:
        """Return models providing the given capability, sorted by priority (descending)."""
        cap = ModelCapability.from_str(capability)
        candidates = [
            m for m in self._models.values()
            if cap in m.capabilities and (not enabled_only or m.enabled)
        ]
        return sorted(candidates, key=lambda m: m.priority, reverse=True)

    def get_highest_priority_model(
        self,
        capability: ModelCapability | str,
        enabled_only: bool = True,
    ) -> ModelDefinition | None:
        """Return the highest-priority enabled model for a capability."""
        matches = self.get_models_for_capability(capability, enabled_only=enabled_only)
        return matches[0] if matches else None


def create_default_registry(default_model_id: str = "openrouter/free") -> ModelRegistry:
    """Factory creating a ModelRegistry pre-populated with standard model targets."""
    registry = ModelRegistry()

    # Core models catalog
    predefined_models = [
        # Router target for OpenRouter free tier
        ModelDefinition(
            id="openrouter/free",
            provider="openrouter",
            capabilities={ModelCapability.GENERAL, ModelCapability.FAST},
            priority=10,
            enabled=True,
            description="OpenRouter free model meta-router target",
        ),
        # High capability general & reasoning
        ModelDefinition(
            id="deepseek/deepseek-r1",
            provider="openrouter",
            capabilities={ModelCapability.REASONING, ModelCapability.CODING},
            priority=50,
            enabled=True,
            description="DeepSeek R1 reasoning specialist",
        ),
        # Coding specialist
        ModelDefinition(
            id="qwen/qwen-2.5-coder-32b-instruct",
            provider="openrouter",
            capabilities={ModelCapability.CODING, ModelCapability.STRUCTURED_OUTPUT},
            priority=40,
            enabled=True,
            description="Qwen 2.5 Coder 32B instruction tuned",
        ),
        # Fast & multimodal
        ModelDefinition(
            id="google/gemini-2.0-flash-001",
            provider="openrouter",
            capabilities={
                ModelCapability.GENERAL,
                ModelCapability.FAST,
                ModelCapability.VISION,
                ModelCapability.TOOL_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            },
            priority=35,
            enabled=True,
            description="Gemini 2.0 Flash high-speed multimodal",
        ),
        # General purpose flagship
        ModelDefinition(
            id="meta-llama/llama-3.3-70b-instruct",
            provider="openrouter",
            capabilities={
                ModelCapability.GENERAL,
                ModelCapability.REASONING,
                ModelCapability.CODING,
                ModelCapability.STRUCTURED_OUTPUT,
            },
            priority=30,
            enabled=True,
            description="Llama 3.3 70B flagship general purpose",
        ),
    ]

    for model in predefined_models:
        registry.register_model(model)

    # Ensure custom configured default_model_id is registered if not already present
    if not registry.get_model(default_model_id):
        registry.register_model(
            ModelDefinition(
                id=default_model_id,
                provider="openrouter",
                capabilities={ModelCapability.GENERAL},
                priority=5,
                enabled=True,
                description="Configured default fallback model",
            )
        )

    return registry
