"""Graceful degradation coordinator with read-only and feature-shedding protections."""

from collections.abc import Awaitable, Callable
import logging
from typing import Any, TypeVar

from app.resilience.schemas import SideEffectType

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceDegradedError(Exception):
    """Raised when an operation cannot be executed in the current degraded mode."""
    pass


class DegradationManager:
    """Manages graceful degradation modes, read-only fallbacks, and feature shedding."""

    def __init__(self) -> None:
        self.is_read_only_mode: bool = False
        self.is_analytics_degraded: bool = False
        self.is_search_degraded: bool = False
        self.is_companion_offline: bool = False

    def set_read_only_mode(self, enabled: bool) -> None:
        logger.warning("Resilience: Degradation read-only mode set to %s", enabled)
        self.is_read_only_mode = enabled

    def check_operation_permitted(self, side_effect_type: SideEffectType) -> None:
        """Enforces that state-mutating operations are blocked during read-only degradation."""
        if self.is_read_only_mode and side_effect_type != SideEffectType.READ_ONLY:
            raise ServiceDegradedError(
                "System is currently running in READ-ONLY DEGRADED MODE. "
                "State-mutating operations are paused to protect data integrity."
            )

    async def execute_optional_feature(
        self,
        feature_name: str,
        feature_callable: Callable[[], Awaitable[T]],
        default_fallback_value: T,
    ) -> T:
        """Executes an optional feature. If it fails, safely sheds the feature without failing the core task."""
        try:
            return await feature_callable()
        except Exception as exc:
            logger.info(
                "Resilience: Optional feature '%s' degraded/unavailable (%s). Returning fallback value.",
                feature_name, exc
            )
            return default_fallback_value
