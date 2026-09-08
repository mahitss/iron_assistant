"""Environment definition and classification for Kairo."""

from enum import Enum


class EnvironmentType(str, Enum):
    """Execution environment mode for Kairo."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    @property
    def is_production(self) -> bool:
        """True if the environment is strictly production."""
        return self == EnvironmentType.PRODUCTION

    @property
    def is_development(self) -> bool:
        """True if the environment is local development."""
        return self == EnvironmentType.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """True if running in an automated test environment."""
        return self == EnvironmentType.TESTING
