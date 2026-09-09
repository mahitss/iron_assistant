"""Personalization, scoped preferences, and cross-tenant isolation for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.learning.personalization")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class UserPreferenceProfile:
    """Scoped behavioral preferences learned or declared for a specific user/project (Spec 87, 89)."""

    user_id: str
    project_id: str | None = None
    output_format: str = "markdown"
    verbosity: str = "normal"  # concise, normal, detailed
    preferred_strategies: dict[str, str] = field(default_factory=dict)  # domain -> strategy_id
    opted_out_of_learning: bool = False
    last_updated: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "project_id": self.project_id,
            "output_format": self.output_format,
            "verbosity": self.verbosity,
            "preferred_strategies": self.preferred_strategies,
            "opted_out_of_learning": self.opted_out_of_learning,
            "last_updated": self.last_updated.isoformat(),
        }


class PersonalizationManager:
    """Manages scoped user preferences and enforces strict cross-user isolation (Spec 89, 90)."""

    def __init__(self) -> None:
        # (user_id, project_id) -> UserPreferenceProfile
        self._profiles: dict[tuple[str, str | None], UserPreferenceProfile] = {}

    def get_profile(self, user_id: str, project_id: str | None = None) -> UserPreferenceProfile:
        """Retrieve profile with strict user-isolation."""
        key = (user_id, project_id)
        if key not in self._profiles:
            self._profiles[key] = UserPreferenceProfile(user_id=user_id, project_id=project_id)
        return self._profiles[key]

    def update_preference(
        self,
        user_id: str,
        project_id: str | None = None,
        output_format: str | None = None,
        verbosity: str | None = None,
        preferred_strategy: tuple[str, str] | None = None,  # (domain, strategy_id)
    ) -> UserPreferenceProfile:
        profile = self.get_profile(user_id, project_id)
        if profile.opted_out_of_learning:
            logger.info("User '%s' has opted out of preference adaptation.", user_id)
            return profile

        if output_format:
            profile.output_format = output_format
        if verbosity:
            profile.verbosity = verbosity
        if preferred_strategy:
            domain, strat_id = preferred_strategy
            profile.preferred_strategies[domain] = strat_id

        profile.last_updated = utc_now()
        return profile

    def reset_preferences(self, user_id: str, project_id: str | None = None) -> None:
        """Reset learned preferences without altering security or audit (Spec 144, 145)."""
        key = (user_id, project_id)
        if key in self._profiles:
            del self._profiles[key]
            logger.info("Reset learned preferences for user '%s' in project '%s'", user_id, project_id)

    def set_learning_opt_out(self, user_id: str, opt_out: bool = True) -> None:
        profile = self.get_profile(user_id)
        profile.opted_out_of_learning = opt_out
        profile.last_updated = utc_now()
