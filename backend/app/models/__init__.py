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
    "AuthenticationError",
    "ChatMessage",
    "DuplicateModelError",
    "HealthResponse",
    "InvalidCapabilityError",
    "MessageRole",
    "ModelCapability",
    "ModelDefinition",
    "ModelNotFoundError",
    "ModelProvider",
    "ModelRegistry",
    "ModelRegistryError",
    "ModelRouter",
    "NoUsableModelError",
    "OpenRouterProvider",
    "ProviderAPIError",
    "ProviderError",
    "RouterError",
    "create_default_registry",
]
