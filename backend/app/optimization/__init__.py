"""Continuous Self-Optimization & Adaptive Control Engine (Task 62)."""

from __future__ import annotations

from app.optimization.engine import OptimizationEngine, optimization_engine
from app.optimization.router import router as optimization_router
from app.optimization.safety import (
    ImmutableControlViolationError,
    KillSwitchActiveError,
    OptimizationExecutionBoundaryError,
    OptimizationSafetyError,
    ParameterBoundsExceededError,
    block_direct_optimization_action,
    optimization_kill_switch,
    sanitize_optimization_directive,
    scrub_optimization_secrets,
    validate_immutable_boundary,
)
from app.optimization.service import OptimizationService, optimization_service

__all__ = [
    "OptimizationEngine",
    "optimization_engine",
    "OptimizationService",
    "optimization_service",
    "optimization_router",
    "OptimizationSafetyError",
    "OptimizationExecutionBoundaryError",
    "ImmutableControlViolationError",
    "ParameterBoundsExceededError",
    "KillSwitchActiveError",
    "block_direct_optimization_action",
    "validate_immutable_boundary",
    "optimization_kill_switch",
    "sanitize_optimization_directive",
    "scrub_optimization_secrets",
]
