"""Tests for typed production configuration and environment validation."""

import pytest
from pydantic import SecretStr

from app.config.environments import EnvironmentType
from app.config.settings import Settings
from app.config.validation import ConfigurationError, validate_environment


def test_development_settings_validate_cleanly():
    """Development settings allow local defaults without crashing startup."""
    settings = Settings(
        ENVIRONMENT=EnvironmentType.DEVELOPMENT,
        DEBUG=True,
        ALLOWED_ORIGINS=["http://localhost:3000"],
    )
    # Does not raise
    validate_environment(settings)
    assert settings.ENVIRONMENT.is_development


def test_testing_settings_validate_cleanly():
    """Testing settings allow test defaults."""
    settings = Settings(
        ENVIRONMENT=EnvironmentType.TESTING,
        DEBUG=False,
        ALLOWED_ORIGINS=["http://testserver"],
    )
    validate_environment(settings)
    assert settings.ENVIRONMENT.is_testing


def test_production_fails_when_secret_key_missing():
    """Production mode must reject missing or weak SECRET_KEY."""
    settings = Settings(
        ENVIRONMENT=EnvironmentType.PRODUCTION,
        SECRET_KEY=None,
        DATABASE_URL="postgresql+asyncpg://usr:pwd@localhost:5432/db",
        REDIS_URL="redis://localhost:6379/0",
        OPENROUTER_API_KEY=SecretStr("sk-or-v1-validkey1234567890abcdef"),
        DEBUG=False,
        ALLOWED_ORIGINS=["https://app.kairo.com"],
    )
    with pytest.raises(ConfigurationError, match="SECRET_KEY must be configured in production"):
        validate_environment(settings)

    # Weak secret key
    weak_settings = Settings(
        ENVIRONMENT=EnvironmentType.PRODUCTION,
        SECRET_KEY=SecretStr("short"),
        DATABASE_URL="postgresql+asyncpg://usr:pwd@localhost:5432/db",
        REDIS_URL="redis://localhost:6379/0",
        OPENROUTER_API_KEY=SecretStr("sk-or-v1-validkey1234567890abcdef"),
        DEBUG=False,
        ALLOWED_ORIGINS=["https://app.kairo.com"],
    )
    with pytest.raises(ConfigurationError, match="at least 32 characters long"):
        validate_environment(weak_settings)


def test_production_fails_when_infrastructure_urls_missing():
    """Production mode must reject missing DATABASE_URL or REDIS_URL."""
    settings = Settings(
        ENVIRONMENT=EnvironmentType.PRODUCTION,
        SECRET_KEY=SecretStr("a_very_secure_production_secret_key_that_is_long_enough"),
        DATABASE_URL=None,
        REDIS_URL=None,
        OPENROUTER_API_KEY=SecretStr("sk-or-v1-validkey1234567890abcdef"),
        DEBUG=False,
        ALLOWED_ORIGINS=["https://app.kairo.com"],
    )
    with pytest.raises(ConfigurationError, match="DATABASE_URL must be configured"):
        validate_environment(settings)


def test_production_fails_when_debug_enabled_or_wildcard_cors():
    """Production mode must reject DEBUG=True and wildcard CORS origins."""
    settings = Settings(
        ENVIRONMENT=EnvironmentType.PRODUCTION,
        SECRET_KEY=SecretStr("a_very_secure_production_secret_key_that_is_long_enough"),
        DATABASE_URL="postgresql+asyncpg://usr:pwd@localhost:5432/db",
        REDIS_URL="redis://localhost:6379/0",
        OPENROUTER_API_KEY=SecretStr("sk-or-v1-validkey1234567890abcdef"),
        DEBUG=True,
        ALLOWED_ORIGINS=["*"],
    )
    with pytest.raises(ConfigurationError) as excinfo:
        validate_environment(settings)

    assert "DEBUG mode must be disabled in production" in str(excinfo.value)
    assert "ALLOWED_ORIGINS must not use wildcard '*'" in str(excinfo.value)
