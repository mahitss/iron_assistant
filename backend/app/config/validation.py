"""Environment and production configuration validation for Kairo."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config.settings import Settings

logger = logging.getLogger("kairo.config.validation")


class ConfigurationError(Exception):
    """Raised when critical configuration constraints are violated."""


def validate_environment(settings: "Settings") -> None:
    """Validate configuration settings, enforcing strict production guarantees."""
    env = settings.ENVIRONMENT

    if env.is_production:
        errors: list[str] = []

        # 1. Secret Key validation
        secret_key = settings.secret_key_str
        if not secret_key:
            errors.append("SECRET_KEY must be configured in production.")
        elif len(secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long in production.")
        elif secret_key in ("secret", "changeme", "default_secret", "kairo_secret"):
            errors.append("SECRET_KEY must not be a predictable default value.")

        # 2. Database URL
        if not settings.DATABASE_URL or not settings.DATABASE_URL.strip():
            errors.append("DATABASE_URL must be configured in production.")

        # 3. Redis URL
        if not settings.REDIS_URL or not settings.REDIS_URL.strip():
            errors.append("REDIS_URL must be configured in production.")

        # 4. OpenRouter API Key
        if not settings.openrouter_api_key_str:
            errors.append("OPENROUTER_API_KEY must be configured in production.")

        # 5. Debug Mode
        if settings.DEBUG:
            errors.append("DEBUG mode must be disabled in production.")

        # 6. CORS Allowed Origins
        origins = (
            settings.ALLOWED_ORIGINS
            if isinstance(settings.ALLOWED_ORIGINS, list)
            else [settings.ALLOWED_ORIGINS]
        )
        if not origins:
            errors.append("ALLOWED_ORIGINS must specify allowed frontend domains in production.")
        elif "*" in origins:
            errors.append("ALLOWED_ORIGINS must not use wildcard '*' in production.")
        else:
            for origin in origins:
                lower_origin = origin.lower()
                if "localhost" in lower_origin or "127.0.0.1" in lower_origin or "::1" in lower_origin:
                    errors.append(
                        f"ALLOWED_ORIGINS must not contain localhost or local loopback in production: {origin}"
                    )

        if errors:
            err_msg = "Production configuration validation failed:\n" + "\n".join(f"- {e}" for e in errors)
            logger.critical(err_msg)
            raise ConfigurationError(err_msg)

        logger.info("Production configuration validated successfully.")
    else:
        # Development / Testing warnings
        if not settings.DATABASE_URL:
            logger.info(
                "Non-production environment: DATABASE_URL not set; in-memory/mock storage may be used."
            )
        if not settings.REDIS_URL:
            logger.info("Non-production environment: REDIS_URL not set; in-memory session cache active.")
        if not settings.openrouter_api_key_str:
            logger.debug("Non-production environment: OPENROUTER_API_KEY not set; mocked providers expected.")
