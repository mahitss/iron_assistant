"""Bounded adjustable parameters registry and constraint clamping for Adaptive Control (Task 62)."""

from __future__ import annotations

import logging

from app.optimization.safety import (
    OptimizationSafetyError,
    ParameterBoundsExceededError,
    validate_immutable_boundary,
)
from app.optimization.schemas import AdjustableParameter, RiskLevel

logger = logging.getLogger(__name__)


class AdjustableParameterRegistry:
    """Maintains the explicit catalog of safely optimizable parameters with inviolable bounds.

    Invariant 7 & 8: Every adjustable parameter has minimum, maximum, default, current_value,
    max_step_change, approval_requirement, and risk_level. Attempts to optimize outside bounds fail closed.
    """

    def __init__(self) -> None:
        self._parameters: dict[str, AdjustableParameter] = {}
        self._register_default_parameters()

    def _register_default_parameters(self) -> None:
        """Register bounded operational parameters permitted for adaptive tuning."""
        defaults = [
            AdjustableParameter(
                parameter_name="model_routing_latency_weight",
                description="Weight given to response latency in dynamic model routing",
                minimum=0.0,
                maximum=1.0,
                default_value=0.5,
                current_value=0.5,
                max_step_change=0.2,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="routing",
            ),
            AdjustableParameter(
                parameter_name="model_routing_cost_weight",
                description="Weight given to inference cost in dynamic model routing",
                minimum=0.0,
                maximum=1.0,
                default_value=0.5,
                current_value=0.5,
                max_step_change=0.2,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="routing",
            ),
            AdjustableParameter(
                parameter_name="cache_ttl_seconds",
                description="Time-to-live for non-sensitive read-through cache",
                minimum=30.0,
                maximum=3600.0,
                default_value=300.0,
                current_value=300.0,
                max_step_change=120.0,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="cache",
            ),
            AdjustableParameter(
                parameter_name="cache_max_size_mb",
                description="Maximum memory allocated to memory cache partition",
                minimum=64.0,
                maximum=2048.0,
                default_value=256.0,
                current_value=256.0,
                max_step_change=128.0,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="cache",
            ),
            AdjustableParameter(
                parameter_name="batch_size_items",
                description="Batch size for asynchronous event ingestion",
                minimum=1.0,
                maximum=100.0,
                default_value=10.0,
                current_value=10.0,
                max_step_change=10.0,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="ingestion",
            ),
            AdjustableParameter(
                parameter_name="retry_backoff_base_seconds",
                description="Initial exponential backoff delay for idempotent external calls",
                minimum=0.5,
                maximum=10.0,
                default_value=1.0,
                current_value=1.0,
                max_step_change=1.0,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="resilience",
            ),
            AdjustableParameter(
                parameter_name="task_priority_boost",
                description="Priority boost factor for near-deadline plan tasks",
                minimum=0.0,
                maximum=10.0,
                default_value=1.0,
                current_value=1.0,
                max_step_change=2.0,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="planning",
            ),
            AdjustableParameter(
                parameter_name="detection_sensitivity_threshold",
                description="Z-score threshold for non-critical anomaly observation",
                minimum=1.5,
                maximum=4.5,
                default_value=3.0,
                current_value=3.0,
                max_step_change=0.5,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                scope="detection",
            ),
            AdjustableParameter(
                parameter_name="timeout_seconds",
                description="Timeout window for standard diagnostic operations",
                minimum=5.0,
                maximum=120.0,
                default_value=30.0,
                current_value=30.0,
                max_step_change=15.0,
                requires_approval=True,
                risk_level=RiskLevel.MEDIUM,
                scope="runtime",
            ),
            AdjustableParameter(
                parameter_name="resource_concurrency_limit",
                description="Worker concurrency cap for background orchestration tasks",
                minimum=2.0,
                maximum=50.0,
                default_value=8.0,
                current_value=8.0,
                max_step_change=4.0,
                requires_approval=True,
                risk_level=RiskLevel.MEDIUM,
                scope="orchestration",
            ),
        ]
        for p in defaults:
            self._parameters[p.parameter_name] = p

    def get_parameter(self, name: str) -> AdjustableParameter | None:
        """Retrieve parameter definition by name."""
        return self._parameters.get(name)

    def list_parameters(self, scope: str | None = None) -> list[AdjustableParameter]:
        """List registered optimizable parameters."""
        if scope:
            return [p for p in self._parameters.values() if p.scope == scope]
        return list(self._parameters.values())

    def validate_and_clamp(
        self,
        parameter_name: str,
        proposed_value: float,
        actor: str = "OPTIMIZER",
    ) -> float:
        """Validate proposed value against bounds and max step change.

        Raises:
            OptimizationSafetyError: If parameter is not registered or touches immutable boundary.
            ParameterBoundsExceededError: If value violates [min, max] or max step change.
        """
        # Invariant 8: Immutable boundary protection
        validate_immutable_boundary(parameter_name, proposed_action=f"Set to {proposed_value}")

        param = self._parameters.get(parameter_name)
        if not param:
            raise OptimizationSafetyError(
                f"PARAMETER_UNREGISTERED: '{parameter_name}' is not registered for self-optimization."
            )

        # Enforce absolute limits
        if proposed_value < param.minimum or proposed_value > param.maximum:
            raise ParameterBoundsExceededError(
                f"BOUNDS_EXCEEDED: Parameter '{parameter_name}' proposed value {proposed_value} "
                f"is outside permitted range [{param.minimum}, {param.maximum}]."
            )

        # Enforce step limits to avoid dangerous sudden shocks
        delta = abs(proposed_value - param.current_value)
        if delta > param.max_step_change + 1e-6:
            raise ParameterBoundsExceededError(
                f"STEP_CHANGE_EXCEEDED: Parameter '{parameter_name}' step delta {delta:.2f} "
                f"exceeds maximum allowed step change {param.max_step_change:.2f}."
            )

        return proposed_value

    def apply_value(self, parameter_name: str, new_value: float) -> None:
        """Update current value of parameter after validation and approval."""
        self.validate_and_clamp(parameter_name, new_value)
        self._parameters[parameter_name].current_value = new_value
        logger.info(
            "PARAMETER_UPDATED: %s set to %f",
            parameter_name,
            new_value,
        )


adjustable_parameter_registry = AdjustableParameterRegistry()
