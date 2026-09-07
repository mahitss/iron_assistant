"""Pydantic models, schemas, provider protocols, and model routing for Kairo."""

from .health import HealthResponse
from .openrouter import OpenRouterProvider
from .provider import (
    AuthenticationError,
    ChatMessage,
    MessageRole,
    ModelProvider,
    ProviderAPIError,
    ProviderError,
)
from .registry import (
    DuplicateModelError,
    ModelCapability,
    ModelDefinition,
    ModelNotFoundError,
    ModelRegistry,
    ModelRegistryError,
    create_default_registry,
)
from .router import (
    InvalidCapabilityError,
    ModelRouter,
    NoUsableModelError,
    RouterError,
)

__all__ = [
    "HealthResponse",
    "ChatMessage",
    "MessageRole",
    "ModelProvider",
    "ProviderError",
    "AuthenticationError",
    "ProviderAPIError",
    "OpenRouterProvider",
    "ModelCapability",
    "ModelDefinition",
    "ModelRegistry",
    "ModelRegistryError",
    "DuplicateModelError",
    "ModelNotFoundError",
    "create_default_registry",
    "ModelRouter",
    "RouterError",
    "InvalidCapabilityError",
    "NoUsableModelError",
]
