"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = "Kairo Personal AI Assistant"
    VERSION: str = "0.5.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # CORS configuration
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # OpenRouter & Model Configuration
    OPENROUTER_API_KEY: SecretStr | None = None
    KAIRO_MODEL: str = "openrouter/free"
    KAIRO_ROUTING_ENABLED: bool = True
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL: str | None = None
    OPENROUTER_APP_NAME: str = "Kairo"

    # Database & Memory Configuration (Task 5)
    DATABASE_URL: str | None = None  # e.g., "postgresql+asyncpg://postgres:postgres@localhost:5432/kairo"
    REDIS_URL: str | None = None     # e.g., "redis://localhost:6379/0"

    # Embedding Provider Configuration
    KAIRO_EMBEDDING_PROVIDER: str | None = None  # e.g., "mock", "openrouter", "openai"
    KAIRO_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Memory & Context Window Constraints
    KAIRO_MEMORY_TOP_K: int = 5
    KAIRO_MAX_CONTEXT_MESSAGES: int = 20
    KAIRO_REDIS_TTL_SECONDS: int = 3600

    @property
    def openrouter_api_key_str(self) -> str:
        """Safely retrieve the raw API key string without exposing it in repr."""
        if self.OPENROUTER_API_KEY:
            return self.OPENROUTER_API_KEY.get_secret_value().strip()
        return ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
