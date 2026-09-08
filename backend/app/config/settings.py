"""Application settings using Pydantic BaseSettings."""

import os
from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.environments import EnvironmentType


class Settings(BaseSettings):
    """Authoritative typed settings schema for Kairo."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = "Kairo Personal AI Assistant"
    VERSION: str = "1.0.0"
    GIT_SHA: str = "dev"
    BUILD_TIMESTAMP: str = ""
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Domain URLs for Deployment
    KAIRO_PUBLIC_API_URL: str | None = None
    KAIRO_FRONTEND_URL: str | None = None

    # Security & Secret Key
    SECRET_KEY: SecretStr | None = None

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

    # Database & Memory Configuration
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    # Database Connection Pool Settings
    KAIRO_DB_POOL_SIZE: int = 10
    KAIRO_DB_MAX_OVERFLOW: int = 20
    KAIRO_DB_POOL_TIMEOUT: int = 30
    KAIRO_DB_POOL_RECYCLE: int = 1800

    # Authentication & Session Security
    KAIRO_AUTH_SESSION_TTL_SECONDS: int = 86400  # 24 hours absolute expiration
    KAIRO_AUTH_IDLE_TIMEOUT_SECONDS: int = 1800  # 30 minutes idle timeout
    KAIRO_AUTH_TOKEN_EXPIRE_MINUTES: int = 1440

    # Rate Limiting
    KAIRO_RATE_LIMIT_ENABLED: bool = True
    KAIRO_RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    KAIRO_RATE_LIMIT_CHAT_PER_MINUTE: int = 30
    KAIRO_RATE_LIMIT_TOOLS_PER_MINUTE: int = 60
    KAIRO_RATE_LIMIT_MEDIA_PER_MINUTE: int = 20

    # Body Size Limits
    KAIRO_MAX_REQUEST_BODY_BYTES: int = 10485760  # 10MB limit

    # Observability & Metrics
    KAIRO_METRICS_ENABLED: bool = True
    KAIRO_TRACING_ENABLED: bool = True

    # Circuit Breaker & Provider Resilience
    KAIRO_CIRCUIT_BREAKER_FAIL_MAX: int = 5
    KAIRO_CIRCUIT_BREAKER_RESET_TIMEOUT: float = 30.0
    KAIRO_PROVIDER_MAX_RETRIES: int = 3
    KAIRO_PROVIDER_INITIAL_BACKOFF_SECONDS: float = 0.5

    # Embedding Provider Configuration
    KAIRO_EMBEDDING_PROVIDER: str | None = None
    KAIRO_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Memory & Context Window Constraints
    KAIRO_MEMORY_TOP_K: int = 5
    KAIRO_MAX_CONTEXT_MESSAGES: int = 20
    KAIRO_REDIS_TTL_SECONDS: int = 3600

    # Personal Context Engine Configuration (Task 20)
    KAIRO_CONTEXT_ENABLED: bool = True
    KAIRO_MEMORY_ENABLED: bool = True
    KAIRO_PROJECT_CONTEXT_ENABLED: bool = True
    KAIRO_PROACTIVE_CONTEXT_ENABLED: bool = True

    KAIRO_MAX_CONTEXT_ITEMS: int = 30
    KAIRO_MAX_MEMORY_ITEMS: int = 10
    KAIRO_MAX_PROJECT_CONTEXT_ITEMS: int = 10

    # Intelligent Memory Extraction
    KAIRO_MEMORY_EXTRACTION_ENABLED: bool = True
    KAIRO_MEMORY_DEDUP_THRESHOLD: float = 0.90
    KAIRO_MEMORY_EXTRACTION_CAPABILITY: str = "fast"

    # Web Research System
    WEB_SEARCH_PROVIDER: str | None = None
    WEB_SEARCH_API_KEY: SecretStr | None = None
    WEB_SEARCH_MAX_RESULTS: int = 5
    WEB_FETCH_MAX_BYTES: int = 2000000
    WEB_FETCH_TIMEOUT_SECONDS: float = 10.0
    WEB_FETCH_MAX_REDIRECTS: int = 3
    WEB_MAX_EXTRACTED_CHARS: int = 30000
    KAIRO_MAX_RESEARCH_ITERATIONS: int = 3
    KAIRO_WEB_CACHE_TTL_SECONDS: int = 900

    # Browser Control System
    KAIRO_BROWSER_ENABLED: bool = True
    KAIRO_BROWSER_HEADLESS: bool = True
    KAIRO_BROWSER_MAX_SESSIONS: int = 3
    KAIRO_BROWSER_SESSION_TIMEOUT_SECONDS: int = 900
    KAIRO_BROWSER_NAVIGATION_TIMEOUT_SECONDS: int = 15
    KAIRO_BROWSER_ACTION_TIMEOUT_SECONDS: int = 10
    KAIRO_BROWSER_MAX_PAGES_PER_SESSION: int = 5
    KAIRO_BROWSER_MAX_TEXT_CHARS: int = 20000
    KAIRO_BROWSER_MAX_ELEMENTS: int = 200
    KAIRO_BROWSER_MAX_LINKS: int = 100

    # Voice System
    KAIRO_VOICE_ENABLED: bool = True
    KAIRO_STT_PROVIDER: str = "mock"
    KAIRO_STT_MODEL: str = "whisper-1"
    KAIRO_STT_API_KEY: SecretStr | None = None
    KAIRO_STT_BASE_URL: str | None = None
    KAIRO_TTS_PROVIDER: str = "mock"
    KAIRO_TTS_MODEL: str = "tts-1"
    KAIRO_TTS_VOICE: str = "alloy"
    KAIRO_TTS_API_KEY: SecretStr | None = None
    KAIRO_TTS_BASE_URL: str | None = None
    KAIRO_VOICE_SAMPLE_RATE: int = 16000
    KAIRO_VOICE_MAX_SESSION_SECONDS: int = 1800
    KAIRO_VOICE_MAX_AUDIO_CHUNK_BYTES: int = 65536
    KAIRO_VOICE_MAX_MESSAGE_SECONDS: int = 60
    KAIRO_VOICE_MAX_CONCURRENT_SESSIONS: int = 5

    # Developer & GitHub Intelligence Settings
    KAIRO_DEVELOPER_ENABLED: bool = True
    KAIRO_REPOSITORY_ROOTS: str = ""
    KAIRO_GITHUB_ENABLED: bool = False
    KAIRO_GITHUB_TOKEN: SecretStr | None = None
    KAIRO_MAX_GIT_LOG_ENTRIES: int = 50
    KAIRO_MAX_DIFF_CHARS: int = 50000
    KAIRO_MAX_CODE_SEARCH_RESULTS: int = 50
    KAIRO_MAX_CODE_SEARCH_FILE_SIZE: int = 1000000
    KAIRO_ALLOWED_TEST_COMMANDS: str = ""

    # Automation & Workflow Engine Settings
    KAIRO_AUTOMATION_ENABLED: bool = True
    KAIRO_WORKFLOW_TIMEOUT_SECONDS: int = 900
    KAIRO_WORKFLOW_STEP_TIMEOUT_SECONDS: int = 120
    KAIRO_MAX_WORKFLOWS_PER_USER: int = 50
    KAIRO_MAX_CONCURRENT_WORKFLOW_RUNS: int = 5
    KAIRO_MIN_SCHEDULE_INTERVAL_SECONDS: int = 60
    KAIRO_WORKFLOW_MAX_RETRIES: int = 3
    KAIRO_APPROVAL_TIMEOUT_SECONDS: int = 30

    # Security, Permissions, Approval & Audit Center Settings
    KAIRO_SECURITY_ENABLED: bool = True
    KAIRO_AUDIT_ENABLED: bool = True
    KAIRO_COMPUTER_ENABLED: bool = False

    # Proactive Intelligence Settings
    KAIRO_PROACTIVE_ENABLED: bool = True
    KAIRO_PROACTIVE_DEDUP_WINDOW_SECONDS: int = 3600
    KAIRO_MAX_PROACTIVE_NOTIFICATIONS_PER_HOUR: int = 20
    KAIRO_MAX_PROACTIVE_INSIGHTS_PER_HOUR: int = 50
    KAIRO_MAX_PROACTIVE_CHAIN_DEPTH: int = 3

    # Multi-Agent Orchestration Settings
    KAIRO_MULTI_AGENT_ENABLED: bool = True
    KAIRO_MAX_AGENT_TASKS: int = 8
    KAIRO_MAX_PARALLEL_AGENTS: int = 3
    KAIRO_AGENT_TIMEOUT_SECONDS: int = 300
    KAIRO_AGENT_TOOL_TIMEOUT_SECONDS: int = 60
    KAIRO_MAX_AGENT_TOOL_CALLS: int = 20
    KAIRO_MAX_TOTAL_AGENT_TOOL_CALLS: int = 50
    KAIRO_MAX_AGENT_TOKENS_PER_TASK: int | None = None
    KAIRO_MAX_TOTAL_AGENT_TOKENS: int | None = None

    @property
    def secret_key_str(self) -> str:
        """Safely retrieve raw secret key without exposing in repr."""
        if self.SECRET_KEY:
            return self.SECRET_KEY.get_secret_value().strip()
        return ""

    @property
    def openrouter_api_key_str(self) -> str:
        """Safely retrieve the raw API key string without exposing it in repr."""
        if self.OPENROUTER_API_KEY:
            return self.OPENROUTER_API_KEY.get_secret_value().strip()
        return ""

    @property
    def stt_api_key_str(self) -> str:
        """Safely retrieve the raw STT API key string."""
        if self.KAIRO_STT_API_KEY:
            return self.KAIRO_STT_API_KEY.get_secret_value().strip()
        return ""

    @property
    def tts_api_key_str(self) -> str:
        """Safely retrieve the raw TTS API key string."""
        if self.KAIRO_TTS_API_KEY:
            return self.KAIRO_TTS_API_KEY.get_secret_value().strip()
        return ""

    @property
    def web_search_api_key_str(self) -> str:
        """Safely retrieve the raw search API key string without exposing it in repr."""
        if self.WEB_SEARCH_API_KEY:
            return self.WEB_SEARCH_API_KEY.get_secret_value().strip()
        return ""

    @property
    def github_token_str(self) -> str:
        """Safely retrieve the raw GitHub token string."""
        if self.KAIRO_GITHUB_TOKEN:
            return self.KAIRO_GITHUB_TOKEN.get_secret_value().strip()
        return ""

    def get_approved_repo_roots(self) -> list[str]:
        """Return canonicalized list of approved repository roots."""
        if not self.KAIRO_REPOSITORY_ROOTS:
            return []
        roots = []
        for r in self.KAIRO_REPOSITORY_ROOTS.split(","):
            cleaned = r.strip()
            if cleaned:
                roots.append(os.path.realpath(cleaned))
        return roots

    def get_allowed_test_commands(self) -> list[str]:
        """Return list of exact approved test commands."""
        if not self.KAIRO_ALLOWED_TEST_COMMANDS:
            return []
        return [c.strip() for c in self.KAIRO_ALLOWED_TEST_COMMANDS.split(",") if c.strip()]

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
