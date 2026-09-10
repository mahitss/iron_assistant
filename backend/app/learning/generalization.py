"""Generalization bounds, scope containment, and anti-overgeneralization guards (INVARIANTS 14-19, 130-133)."""

from __future__ import annotations

from typing import Any
from app.learning.schemas import GeneralizationScope


class OvergeneralizationError(Exception):
    """Raised when an attempt is made to generalize a single or unverified event into a broad rule."""
    pass


class GeneralizationGuard:
    """Enforces scope containment and prevents overgeneralizing isolated events into global rules."""

    SCOPE_HIERARCHY = [
        GeneralizationScope.TASK,
        GeneralizationScope.SESSION,
        GeneralizationScope.PROJECT,
        GeneralizationScope.REPOSITORY,
        GeneralizationScope.ENVIRONMENT,
        GeneralizationScope.USER,
        GeneralizationScope.GLOBAL,
    ]

    MIN_EXPERIENCES_FOR_GLOBAL = 5
    MIN_EXPERIENCES_FOR_USER = 3
    MIN_EXPERIENCES_FOR_REPOSITORY = 2

    @classmethod
    def validate_generalization(
        cls,
        target_scope: GeneralizationScope,
        experience_count: int,
        is_explicit_user_directive: bool = False,
        is_verified_pattern: bool = False,
    ) -> bool:
        """INVARIANT 14, 15, 18: One event must not create broad rules.
        Validates whether supporting evidence qualifies for the requested scope.
        """
        # Explicit user instruction can immediately set USER or PROJECT scope
        if is_explicit_user_directive:
            if target_scope == GeneralizationScope.GLOBAL:
                # Even explicit instruction requires governance for GLOBAL
                if experience_count < 2:
                    raise OvergeneralizationError(
                        "INVARIANT 18: Global generalization requires multi-experience validation even with explicit user instruction."
                    )
            return True

        if target_scope == GeneralizationScope.GLOBAL:
            if experience_count < cls.MIN_EXPERIENCES_FOR_GLOBAL or not is_verified_pattern:
                raise OvergeneralizationError(
                    f"INVARIANT 14 & 18: Cannot generalize to GLOBAL scope with only {experience_count} experience(s). "
                    f"Requires at least {cls.MIN_EXPERIENCES_FOR_GLOBAL} verified multi-source experiences."
                )

        elif target_scope == GeneralizationScope.USER:
            if experience_count < cls.MIN_EXPERIENCES_FOR_USER:
                raise OvergeneralizationError(
                    f"INVARIANT 20: Cannot promote behavior to USER preference with only {experience_count} occurrence(s). "
                    f"Requires at least {cls.MIN_EXPERIENCES_FOR_USER} consistent repetitions."
                )

        elif target_scope in (GeneralizationScope.REPOSITORY, GeneralizationScope.ENVIRONMENT):
            if experience_count < cls.MIN_EXPERIENCES_FOR_REPOSITORY:
                raise OvergeneralizationError(
                    f"INVARIANT 14: Scope {target_scope.value} requires at least {cls.MIN_EXPERIENCES_FOR_REPOSITORY} supporting experiences."
                )

        return True

    @classmethod
    def get_narrowest_scope(cls, detected_scope: str | None = None) -> GeneralizationScope:
        """INVARIANT 17: Use narrowest reasonable scope as default."""
        if not detected_scope:
            return GeneralizationScope.TASK
        try:
            return GeneralizationScope(detected_scope)
        except ValueError:
            return GeneralizationScope.PROJECT

    @classmethod
    def assert_cross_user_isolation(cls, user_a: str, user_b: str, scope: GeneralizationScope) -> None:
        """INVARIANT 133: Never transfer private user learning to another user."""
        if user_a != user_b and scope in (GeneralizationScope.USER, GeneralizationScope.SESSION, GeneralizationScope.TASK):
            raise PermissionError(
                f"INVARIANT 133: Cross-user learning leakage detected from {user_a} to {user_b}. Operation blocked."
            )
