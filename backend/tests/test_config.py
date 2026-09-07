"""Tests for application configuration loading and security."""

from app.core.config import Settings


def test_default_config_values() -> None:
    """Ensure default settings match project standards."""
    settings = Settings(
        OPENROUTER_API_KEY=None,
        _env_file=None,  # Do not load local .env during isolated unit test
    )

    assert settings.KAIRO_MODEL == "openrouter/free"
    assert settings.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
    assert settings.OPENROUTER_APP_NAME == "Kairo"
    assert settings.openrouter_api_key_str == ""


def test_custom_config_values() -> None:
    """Ensure custom settings can be loaded properly."""
    settings = Settings(
        OPENROUTER_API_KEY="test_secret_key_123",  # pragma: allowlist secret
        KAIRO_MODEL="anthropic/claude-3.5-haiku",
        OPENROUTER_APP_NAME="CustomKairo",
        _env_file=None,
    )

    assert settings.KAIRO_MODEL == "anthropic/claude-3.5-haiku"
    assert settings.OPENROUTER_APP_NAME == "CustomKairo"
    assert settings.openrouter_api_key_str == "test_secret_key_123"
    # Ensure raw secret is not leaked in repr/str
    assert "test_secret_key_123" not in repr(settings.OPENROUTER_API_KEY)


def test_cors_origins_parsing() -> None:
    """Ensure comma-separated CORS origins string parses into a list."""
    settings = Settings(
        ALLOWED_ORIGINS="http://localhost:3000,http://app.kairo.local",
        _env_file=None,
    )
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3000", "http://app.kairo.local"]
