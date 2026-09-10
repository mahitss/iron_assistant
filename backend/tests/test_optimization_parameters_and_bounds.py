"""Unit tests for Bounded Adjustable Parameters Registry and Safety Bounds (Task 62)."""

import pytest

from app.optimization.parameters import AdjustableParameterRegistry
from app.optimization.safety import (
    ImmutableControlViolationError,
    OptimizationSafetyError,
    ParameterBoundsExceededError,
)


def test_parameter_registry_initialization_and_listing():
    """Verify registered parameters exist and are queryable by scope."""
    registry = AdjustableParameterRegistry()

    all_params = registry.list_parameters()
    assert len(all_params) >= 8

    routing_params = registry.list_parameters(scope="routing")
    assert len(routing_params) >= 2
    assert any(p.parameter_name == "model_routing_latency_weight" for p in routing_params)


def test_parameter_validation_within_bounds():
    """Verify safe values within [min, max] and max_step_change pass validation."""
    registry = AdjustableParameterRegistry()

    # batch_size_items: current=10, min=1, max=100, max_step=10
    validated = registry.validate_and_clamp("batch_size_items", 15.0)
    assert validated == 15.0


def test_parameter_bounds_exceeded_min_and_max():
    """Test Invariant 7: Parameter bounds are strictly enforced; values outside [min, max] fail closed."""
    registry = AdjustableParameterRegistry()

    # batch_size_items: min=1, max=100
    with pytest.raises(ParameterBoundsExceededError, match="outside permitted range"):
        registry.validate_and_clamp("batch_size_items", 0.0)

    with pytest.raises(ParameterBoundsExceededError, match="outside permitted range"):
        registry.validate_and_clamp("batch_size_items", 150.0)


def test_parameter_step_change_exceeded():
    """Test Invariant 7: Sudden parameter shocks are blocked via max_step_change limits."""
    registry = AdjustableParameterRegistry()

    # cache_ttl_seconds: current=300, max_step_change=120
    # Attempting to jump from 300 to 500 (delta=200 > 120)
    with pytest.raises(ParameterBoundsExceededError, match="STEP_CHANGE_EXCEEDED"):
        registry.validate_and_clamp("cache_ttl_seconds", 500.0)

    # Within step change: 300 -> 360 (delta=60 <= 120)
    assert registry.validate_and_clamp("cache_ttl_seconds", 360.0) == 360.0


def test_unregistered_parameter_rejected():
    """Verify attempting to optimize an unregistered parameter fails closed."""
    registry = AdjustableParameterRegistry()

    with pytest.raises(OptimizationSafetyError, match="PARAMETER_UNREGISTERED"):
        registry.validate_and_clamp("arbitrary_unknown_parameter", 42.0)


def test_immutable_boundary_rejected_at_parameter_level():
    """Test Invariant 8: The optimizer fails closed if attempting to touch immutable security boundaries."""
    registry = AdjustableParameterRegistry()

    with pytest.raises(ImmutableControlViolationError, match="IMMUTABLE_CONTROL_VIOLATION"):
        registry.validate_and_clamp("authorization_policy_mode", 0.0)

    with pytest.raises(ImmutableControlViolationError, match="IMMUTABLE_CONTROL_VIOLATION"):
        registry.validate_and_clamp("security_encryption_level", 1.0)


def test_apply_value_mutates_state_safely():
    """Verify apply_value validates and modifies current value."""
    registry = AdjustableParameterRegistry()

    param = registry.get_parameter("batch_size_items")
    assert param.current_value == 10.0

    registry.apply_value("batch_size_items", 18.0)
    assert registry.get_parameter("batch_size_items").current_value == 18.0
