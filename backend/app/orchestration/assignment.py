"""Provider assignment, fallback chains, validation, and assignment models (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.matching import CapabilityMatcher, capability_matcher
from app.orchestration.safety import (
    AuthorizationMissingError,
    CapabilityUnavailableError,
    OrchestrationSafetyError,
)
from app.orchestration.schemas import (
    AssignmentStatus,
    ProviderAssignment,
    TaskCapabilityRequirement,
)

logger = logging.getLogger(__name__)


class AssignmentEngine:
    """Assigns tasks to vetted providers with fallback chains and validation gates."""

    def __init__(self, matcher: CapabilityMatcher | None = None) -> None:
        self._matcher = matcher or capability_matcher

    def assign_task(
        self,
        requirement: TaskCapabilityRequirement,
        granted_permissions: set[str] | None = None,
        allocated_resources: list[dict[str, Any]] | None = None,
        historical_stats_map: dict[str, dict[str, Any]] | None = None,
    ) -> ProviderAssignment:
        """Select best candidate provider and assign primary and fallback routes."""
        ranked_candidates = self._matcher.rank_candidates(
            requirement=requirement,
            granted_permissions=granted_permissions,
            historical_stats_map=historical_stats_map,
        )

        if not ranked_candidates:
            raise CapabilityUnavailableError(
                f"No registered provider found for capabilities {requirement.required_capabilities} in '{requirement.environment}'."
            )

        primary = ranked_candidates[0]

        # Check authorization gate: Capability != Authorization
        if not primary.is_authorized:
            raise AuthorizationMissingError(
                f"Candidate provider '{primary.provider_name}' has required capability but lacks authorization for permissions: {primary.missing_permissions}."
            )

        if not primary.environment_compatibility:
            raise OrchestrationSafetyError(
                f"Candidate provider '{primary.provider_name}' is not compatible with environment '{requirement.environment}'."
            )

        # Identify fallback provider if available
        fallback_name: str | None = None
        for candidate in ranked_candidates[1:]:
            if candidate.is_authorized and candidate.environment_compatibility:
                fallback_name = candidate.provider_name
                break

        assignment = ProviderAssignment(
            task_id=requirement.task_id,
            provider_name=primary.provider_name,
            provider_type=primary.provider_type,
            capability_id=primary.capability_id,
            allocated_resources=allocated_resources or [],
            required_permissions=requirement.required_permissions,
            status=AssignmentStatus.VALIDATED,
            rationale=primary.rationale,
            confidence=primary.overall_score,
            fallback_provider=fallback_name,
            verification_criteria=requirement.verification_criteria,
        )

        logger.info(
            "TASK_ASSIGNED: task_id=%s provider=%s confidence=%.2f fallback=%s",
            requirement.task_id,
            primary.provider_name,
            primary.overall_score,
            fallback_name,
        )
        return assignment

    def validate_assignment(
        self,
        assignment: ProviderAssignment,
        current_environment: str = "development",
        current_granted_permissions: set[str] | None = None,
    ) -> bool:
        """Revalidate assignment before execution.

        Ensures provider is still authorized and environment hasn't drifted.
        """
        granted = current_granted_permissions or set()
        for perm in assignment.required_permissions:
            if perm not in granted:
                assignment.status = AssignmentStatus.FAILED
                raise AuthorizationMissingError(
                    f"Revalidation failed for task '{assignment.task_id}': missing permission '{perm}'."
                )

        assignment.status = AssignmentStatus.ASSIGNED
        return True


assignment_engine = AssignmentEngine()
