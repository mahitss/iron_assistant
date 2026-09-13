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
    VERSION: str = "1.1.0"
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

    # Knowledge Fabric Configuration (Task 25)
    KAIRO_KNOWLEDGE_ENABLED: bool = True
    KAIRO_KNOWLEDGE_MAX_NODES: int = 15
    KAIRO_KNOWLEDGE_MAX_EDGES: int = 20
    KAIRO_KNOWLEDGE_MAX_DEPTH: int = 3
    KAIRO_KNOWLEDGE_INDEX_MAX_BYTES: int = 10485760  # 10MB document limit
    KAIRO_KNOWLEDGE_CHUNK_SIZE: int = 800
    KAIRO_KNOWLEDGE_CHUNK_OVERLAP: int = 100

    # Skills and Capability System Configuration (Task 26)
    KAIRO_SKILLS_ENABLED: bool = True
    KAIRO_MAX_SKILL_DEPTH: int = 3
    KAIRO_MAX_SKILL_STEPS: int = 20
    KAIRO_MAX_TOOL_CALLS_PER_SKILL: int = 50
    KAIRO_SKILL_TIMEOUT_SECONDS: int = 300

    # Evaluation, Benchmarking & Quality Gates Configuration (Task 27)
    KAIRO_EVAL_ENABLED: bool = True
    KAIRO_EVAL_MODE: str = "LOCAL"  # LOCAL, CI, STAGING
    KAIRO_EVAL_MOCK_MODE: bool = True
    KAIRO_EVAL_SECURITY_MIN: float = 1.0  # Strict 100% security gate
    KAIRO_EVAL_TOOL_SELECTION_MIN: float = 0.90
    KAIRO_EVAL_CONTEXT_PRECISION_MIN: float = 0.80
    KAIRO_EVAL_ROUTING_MIN: float = 0.85
    KAIRO_EVAL_MAX_P95_LATENCY_MS: float = 5000.0

    # Unified Event Bus & Event-Driven Runtime Configuration (Task 28)
    KAIRO_EVENTS_ENABLED: bool = True
    KAIRO_EVENTS_MAX_IN_MEMORY_QUEUE: int = 2000
    KAIRO_EVENTS_DEFAULT_RETRY_LIMIT: int = 3
    KAIRO_EVENTS_INITIAL_BACKOFF_SECONDS: float = 0.5
    KAIRO_EVENTS_MAX_BACKOFF_SECONDS: float = 60.0
    KAIRO_EVENTS_OUTBOX_POLL_INTERVAL_SECONDS: float = 2.0
    KAIRO_EVENTS_DEDUP_WINDOW_SECONDS: int = 3600
    KAIRO_EVENTS_DEAD_LETTER_RETENTION_DAYS: int = 30

    # Experience Learning & Feedback Loop Configuration (Task 29)
    KAIRO_EXPERIENCE_ENABLED: bool = True
    KAIRO_MAX_EXPERIENCE_CONTEXT: int = 10
    KAIRO_MAX_PREFERENCE_CONTEXT: int = 10
    KAIRO_EXPERIENCE_DECAY_DAYS: int = 90
    KAIRO_EXPERIENCE_AUTO_STALE_ON_PROJECT_CHANGE: bool = True

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

    # Multimodal Intelligence Layer Settings (Task 30)
    KAIRO_MULTIMODAL_ENABLED: bool = True
    KAIRO_MULTIMODAL_MOCK_MODE: bool = True
    KAIRO_MAX_IMAGE_SIZE_BYTES: int = 15728640  # 15MB
    KAIRO_MAX_AUDIO_SIZE_BYTES: int = 26214400  # 25MB
    KAIRO_MAX_VIDEO_SIZE_BYTES: int = 52428800  # 50MB
    KAIRO_MAX_DOCUMENT_SIZE_BYTES: int = 20971520  # 20MB
    KAIRO_MAX_AUDIO_DURATION_SECONDS: int = 300  # 5 minutes
    KAIRO_MAX_VIDEO_DURATION_SECONDS: int = 180  # 3 minutes
    KAIRO_MAX_VIDEO_FRAMES: int = 30
    KAIRO_VIDEO_SAMPLE_INTERVAL_SECONDS: int = 5
    KAIRO_MAX_IMAGE_DIMENSION: int = 4096
    KAIRO_MAX_MULTIMODAL_IMAGES: int = 5
    KAIRO_MAX_MULTIMODAL_DOCUMENT_CHUNKS: int = 10
    KAIRO_MAX_MULTIMODAL_CONTEXT_TOKENS: int = 8000
    KAIRO_SCREEN_CAPTURE_EPHEMERAL: bool = True

    # Autonomous Task Engine Settings (Task 31)
    KAIRO_TASKS_ENABLED: bool = True
    KAIRO_TASK_MAX_STEPS: int = 20
    KAIRO_TASK_MAX_TOOL_CALLS: int = 50
    KAIRO_TASK_MAX_AGENTS: int = 5
    KAIRO_TASK_MAX_DURATION: int = 1800  # 30 minutes
    KAIRO_TASK_MAX_COST: float = 10.0  # Max cost in USD
    KAIRO_TASK_MAX_REPLANS: int = 5
    KAIRO_TASK_MAX_RETRIES: int = 3
    KAIRO_TASK_MAX_PARALLEL_STEPS: int = 4
    KAIRO_MAX_ACTIVE_TASKS_PER_USER: int = 5
    KAIRO_MAX_ACTIVE_TASKS_PER_PROJECT: int = 10
    KAIRO_TASK_APPROVAL_TIMEOUT_SECONDS: int = 900  # 15 minutes

    # World Model & Environment State Settings (Task 32)
    KAIRO_WORLD_ENABLED: bool = True
    KAIRO_WORLD_MAX_ENTITIES_PER_QUERY: int = 100
    KAIRO_WORLD_MAX_RELATIONSHIP_DEPTH: int = 3
    KAIRO_WORLD_QUERY_TIMEOUT_SECONDS: float = 5.0
    KAIRO_WORLD_RECONCILIATION_INTERVAL_SECONDS: int = 300
    KAIRO_WORLD_MAX_SNAPSHOTS_PER_USER: int = 20
    KAIRO_WORLD_SNAPSHOT_MAX_ENTITIES: int = 500

    # Identity, Session, Device Trust, Presence & Handoff Settings (Task 33)
    KAIRO_IDENTITY_ENABLED: bool = True
    KAIRO_IDENTITY_MAX_SESSIONS_PER_USER: int = 10
    KAIRO_IDENTITY_MAX_DEVICES_PER_USER: int = 15
    KAIRO_IDENTITY_SESSION_TTL_SECONDS: int = 86400  # 24 hours default TTL
    KAIRO_IDENTITY_SESSION_IDLE_TIMEOUT_SECONDS: int = 3600  # 1 hour idle timeout
    KAIRO_IDENTITY_HANDOFF_TTL_SECONDS: int = 300  # 5 minutes handoff ticket TTL
    KAIRO_IDENTITY_PAIRING_TTL_SECONDS: int = 600  # 10 minutes pairing code TTL
    KAIRO_IDENTITY_PRESENCE_TIMEOUT_SECONDS: int = 90  # 90s presence disconnect threshold
    KAIRO_IDENTITY_TRUST_EXPIRATION_DAYS: int = 90  # 90 days device trust validity

    # Unified Notification & Alerting Layer Settings (Task 34)
    KAIRO_NOTIFICATIONS_ENABLED: bool = True
    KAIRO_NOTIFICATION_RATE_LIMIT_PER_MINUTE: int = 30
    KAIRO_NOTIFICATION_RATE_LIMIT_PER_HOUR: int = 200
    KAIRO_NOTIFICATION_DEDUPE_WINDOW_SECONDS: int = 300  # 5 minutes
    KAIRO_NOTIFICATION_GROUPING_WINDOW_SECONDS: int = 60  # 1 minute
    KAIRO_NOTIFICATION_STORM_THRESHOLD: int = 20  # 20 events within 10s triggers storm collapse
    KAIRO_NOTIFICATION_RETENTION_DAYS: int = 30
    KAIRO_NOTIFICATION_MAX_DELIVERY_RETRIES: int = 3
    KAIRO_NOTIFICATION_DEFAULT_EXPIRY_SECONDS: int = 86400  # 24 hours

    # Native Runtime Substrate Configuration (Task 80)
    KAIRO_NATIVE_RUNTIME_MODE: str = "OPTIONAL"  # OPTIONAL, REQUIRED, DISABLED
    KAIRO_NATIVE_RUNTIME_HOST: str = "127.0.0.1"
    KAIRO_NATIVE_RUNTIME_PORT: int = 8788
    KAIRO_NATIVE_RUNTIME_SECRET: str | None = None
    KAIRO_NATIVE_RUNTIME_MAX_MESSAGE_BYTES: int = 1048576  # 1MB
    KAIRO_NATIVE_RUNTIME_TIMEOUT_SECONDS: float = 30.0

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


# Convenient singleton alias
settings: Settings = get_settings()
