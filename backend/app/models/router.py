"""Model router for selecting models based on capability, priority, and availability."""

from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry


class RouterError(Exception):
    """Base exception for routing errors."""


class InvalidCapabilityError(RouterError):
    """Raised when an unknown or invalid capability is requested."""


class NoUsableModelError(RouterError):
    """Raised when no compatible and enabled model is available."""


class ModelRouter:
    """Intelligent router selecting the optimal enabled model for requested task capabilities."""

    def __init__(
        self,
        registry: ModelRegistry,
        default_model_id: str = "openrouter/free",
        routing_enabled: bool = True,
    ) -> None:
        self.registry = registry
        self.default_model_id = default_model_id
        self.routing_enabled = routing_enabled

    def select_model(
        self,
        capability: ModelCapability | str = ModelCapability.GENERAL,
    ) -> ModelDefinition:
        """Select the highest-priority enabled model for a capability, or fall back to default."""
        try:
            cap = ModelCapability.from_str(capability)
        except ValueError as exc:
            raise InvalidCapabilityError(str(exc))

        # If capability-based routing is globally disabled, immediately route to default
        if not self.routing_enabled:
            return self._get_fallback_model(
                f"Routing disabled; falling back to default '{self.default_model_id}'"
            )

        # 1. Try to find highest priority enabled model for the requested capability
        best_match = self.registry.get_highest_priority_model(cap, enabled_only=True)
        if best_match is not None:
            return best_match

        # 2. Fall back to configured default model if no compatible model exists
        return self._get_fallback_model(
            f"No enabled model found for capability '{cap.value}'. Falling back to default '{self.default_model_id}'"
        )

    def _get_fallback_model(self, reason: str) -> ModelDefinition:
        """Retrieve and validate the default fallback model."""
        fallback = self.registry.get_model(self.default_model_id)

        if fallback is None or not fallback.enabled:
            raise NoUsableModelError(
                f"No usable model available: default fallback model '{self.default_model_id}' "
                f"is either missing or disabled. ({reason})"
            )

        return fallback
