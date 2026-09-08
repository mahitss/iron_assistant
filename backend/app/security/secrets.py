"""Secrets management abstraction providing secure credential access."""

import os
from abc import ABC, abstractmethod

from app.config.settings import get_settings


class SecretProvider(ABC):
    """Abstract base contract for secret retrieval."""

    @abstractmethod
    def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Retrieve secret by key."""
        ...

    @abstractmethod
    def has_secret(self, key: str) -> bool:
        """Check if secret exists."""
        ...


class EnvSecretProvider(SecretProvider):
    """Environment-based secret provider for containerized and 12-factor deployments."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Fetch secret value from environment or settings without exposing it in logs."""
        val = os.getenv(key)
        if val is not None and val.strip():
            return val.strip()

        # Fallback check on Settings object for typed secrets
        settings = get_settings()
        attr_map = {
            "SECRET_KEY": settings.secret_key_str,
            "OPENROUTER_API_KEY": settings.openrouter_api_key_str,
            "KAIRO_GITHUB_TOKEN": settings.github_token_str,
            "WEB_SEARCH_API_KEY": settings.web_search_api_key_str,
            "KAIRO_STT_API_KEY": settings.stt_api_key_str,
            "KAIRO_TTS_API_KEY": settings.tts_api_key_str,
        }
        if key in attr_map and attr_map[key]:
            return attr_map[key]

        return default

    def has_secret(self, key: str) -> bool:
        """Check whether the given secret key is populated."""
        val = self.get_secret(key)
        return bool(val)


_DEFAULT_PROVIDER: SecretProvider | None = None


def get_secret_provider() -> SecretProvider:
    """Return the active secret provider singleton."""
    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        _DEFAULT_PROVIDER = EnvSecretProvider()
    return _DEFAULT_PROVIDER


def set_secret_provider(provider: SecretProvider) -> None:
    """Set custom secret provider (e.g. for testing or cloud vault integration)."""
    global _DEFAULT_PROVIDER
    _DEFAULT_PROVIDER = provider
