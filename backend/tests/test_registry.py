"""Tests for ModelCapability, ModelDefinition, and ModelRegistry."""

import pytest

from app.models.registry import (
    DuplicateModelError,
    ModelCapability,
    ModelDefinition,
    ModelRegistry,
    create_default_registry,
)


def test_model_capability_from_str() -> None:
    """Ensure capability string parsing is case-insensitive and validates properly."""
    assert ModelCapability.from_str("coding") == ModelCapability.CODING
    assert ModelCapability.from_str("REASONING") == ModelCapability.REASONING
    assert ModelCapability.from_str("  fast  ") == ModelCapability.FAST

    with pytest.raises(ValueError) as exc_info:
        ModelCapability.from_str("quantum_teleportation")
    assert "Unknown capability" in str(exc_info.value)


def test_registry_registration_and_retrieval() -> None:
    """Ensure models can be registered and retrieved by ID."""
    registry = ModelRegistry()
    model = ModelDefinition(
        id="test/model-1",
        provider="openrouter",
        capabilities={ModelCapability.GENERAL, ModelCapability.CODING},
        priority=10,
        enabled=True,
    )
    registry.register_model(model)

    retrieved = registry.get_model("test/model-1")
    assert retrieved is not None
    assert retrieved.id == "test/model-1"
    assert retrieved.priority == 10
    assert ModelCapability.CODING in retrieved.capabilities


def test_duplicate_model_registration_handling() -> None:
    """Ensure duplicate model ID registration raises DuplicateModelError unless overridden."""
    registry = ModelRegistry()
    model1 = ModelDefinition(id="test/dup", priority=10)
    model2 = ModelDefinition(id="test/dup", priority=20)

    registry.register_model(model1)

    with pytest.raises(DuplicateModelError):
        registry.register_model(model2, allow_override=False)

    # Overwrite allowed
    registry.register_model(model2, allow_override=True)
    assert registry.get_model("test/dup").priority == 20


def test_capability_filtering_and_priority_sorting() -> None:
    """Ensure filtering by capability sorts models by descending priority."""
    registry = ModelRegistry()
    m_low = ModelDefinition(id="m_low", capabilities={ModelCapability.CODING}, priority=5)
    m_high = ModelDefinition(id="m_high", capabilities={ModelCapability.CODING}, priority=50)
    m_mid = ModelDefinition(
        id="m_mid", capabilities={ModelCapability.CODING, ModelCapability.GENERAL}, priority=25
    )
    m_other = ModelDefinition(id="m_other", capabilities={ModelCapability.VISION}, priority=100)

    for m in [m_low, m_high, m_mid, m_other]:
        registry.register_model(m)

    coding_models = registry.get_models_for_capability(ModelCapability.CODING)
    assert [m.id for m in coding_models] == ["m_high", "m_mid", "m_low"]

    best = registry.get_highest_priority_model(ModelCapability.CODING)
    assert best is not None
    assert best.id == "m_high"


def test_disabled_model_exclusion() -> None:
    """Ensure disabled models are excluded when enabled_only is True."""
    registry = ModelRegistry()
    m_active = ModelDefinition(id="active", capabilities={ModelCapability.FAST}, priority=10, enabled=True)
    m_disabled = ModelDefinition(
        id="disabled", capabilities={ModelCapability.FAST}, priority=99, enabled=False
    )

    registry.register_model(m_active)
    registry.register_model(m_disabled)

    best = registry.get_highest_priority_model(ModelCapability.FAST, enabled_only=True)
    assert best is not None
    assert best.id == "active"

    # Listing disabled models explicitly
    all_fast = registry.get_models_for_capability(ModelCapability.FAST, enabled_only=False)
    assert len(all_fast) == 2
    assert all_fast[0].id == "disabled"


def test_default_registry_creation() -> None:
    """Ensure default registry populates openrouter/free and standard targets."""
    registry = create_default_registry(default_model_id="openrouter/free")
    free_target = registry.get_model("openrouter/free")

    assert free_target is not None
    assert free_target.enabled is True
    assert ModelCapability.GENERAL in free_target.capabilities

    # Custom default model gets registered if not existing
    custom_reg = create_default_registry(default_model_id="custom/custom-fallback")
    custom_target = custom_reg.get_model("custom/custom-fallback")
    assert custom_target is not None
    assert custom_target.enabled is True
