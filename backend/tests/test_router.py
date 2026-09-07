"""Tests for ModelRouter selection logic and fallback mechanisms."""

import pytest
from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry
from app.models.router import InvalidCapabilityError, ModelRouter, NoUsableModelError


@pytest.fixture
def populated_registry() -> ModelRegistry:
    """Provide a populated registry for router tests."""
    registry = ModelRegistry()

    models = [
        ModelDefinition(
            id="openrouter/free",
            capabilities={ModelCapability.GENERAL, ModelCapability.FAST},
            priority=10,
            enabled=True,
        ),
        ModelDefinition(
            id="deepseek/deepseek-r1",
            capabilities={ModelCapability.REASONING, ModelCapability.CODING},
            priority=50,
            enabled=True,
        ),
        ModelDefinition(
            id="qwen/qwen-2.5-coder-32b-instruct",
            capabilities={ModelCapability.CODING},
            priority=60,
            enabled=True,
        ),
        ModelDefinition(
            id="disabled/coder",
            capabilities={ModelCapability.CODING},
            priority=100,
            enabled=False,
        ),
    ]
    for m in models:
        registry.register_model(m)
    return registry


def test_select_highest_priority_model_for_capability(populated_registry: ModelRegistry) -> None:
    """Ensure router picks the enabled model with the highest priority for a capability."""
    router = ModelRouter(registry=populated_registry, default_model_id="openrouter/free")

    # Coding: qwen (priority 60) should be chosen over disabled/coder (100) and deepseek (50)
    selected = router.select_model(ModelCapability.CODING)
    assert selected.id == "qwen/qwen-2.5-coder-32b-instruct"

    # Reasoning: deepseek-r1
    selected_reasoning = router.select_model("reasoning")
    assert selected_reasoning.id == "deepseek/deepseek-r1"


def test_fallback_to_default_when_no_compatible_model(populated_registry: ModelRegistry) -> None:
    """Ensure router falls back to default model when requested capability has no match."""
    router = ModelRouter(registry=populated_registry, default_model_id="openrouter/free")

    # Vision has no compatible model in populated_registry -> fall back to openrouter/free
    selected = router.select_model(ModelCapability.VISION)
    assert selected.id == "openrouter/free"


def test_fallback_when_routing_disabled(populated_registry: ModelRegistry) -> None:
    """Ensure router always chooses default model if routing_enabled is False."""
    router = ModelRouter(
        registry=populated_registry,
        default_model_id="openrouter/free",
        routing_enabled=False,
    )

    # Even for coding, routing disabled returns openrouter/free
    selected = router.select_model(ModelCapability.CODING)
    assert selected.id == "openrouter/free"


def test_missing_default_model_raises_no_usable_model_error() -> None:
    """Ensure router raises NoUsableModelError if default model is not registered."""
    empty_registry = ModelRegistry()
    router = ModelRouter(registry=empty_registry, default_model_id="nonexistent-model")

    with pytest.raises(NoUsableModelError) as exc_info:
        router.select_model(ModelCapability.GENERAL)
    assert "nonexistent-model" in str(exc_info.value)


def test_disabled_default_model_raises_no_usable_model_error() -> None:
    """Ensure router raises NoUsableModelError if default model exists but is disabled."""
    registry = ModelRegistry()
    registry.register_model(ModelDefinition(id="def-model", enabled=False))

    router = ModelRouter(registry=registry, default_model_id="def-model")
    with pytest.raises(NoUsableModelError):
        router.select_model(ModelCapability.GENERAL)


def test_unknown_capability_raises_invalid_capability_error(populated_registry: ModelRegistry) -> None:
    """Ensure passing an unknown capability string raises InvalidCapabilityError."""
    router = ModelRouter(registry=populated_registry, default_model_id="openrouter/free")

    with pytest.raises(InvalidCapabilityError) as exc_info:
        router.select_model("super_sentient_intelligence")
    assert "Unknown capability" in str(exc_info.value)
