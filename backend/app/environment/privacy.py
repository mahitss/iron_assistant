"""Privacy Guard, Sensitive Data Scrubbing, and Log Minimization (Task 54, Prompts #181-#192)."""

from __future__ import annotations

import re
from typing import Any

from app.environment.safety import EnvironmentSafetyGuard


class PrivacyGuard:
    """Enforces boundaries, data minimization, and secret scrubbing across environment data."""

    @staticmethod
    def sanitize_configuration(config_dict: dict[str, Any]) -> dict[str, Any]:
        """Prompt #187, #190: Redacts sensitive parameters from configuration dictionaries."""
        return EnvironmentSafetyGuard.inspect_and_sanitize_metadata(config_dict, raise_on_secret=False)

    @staticmethod
    def extract_log_reference(log_output: str, max_chars: int = 500) -> dict[str, Any]:
        """Prompt #191, #192: Log privacy: Do not ingest full logs; store reference and trimmed snippet."""
        trimmed = log_output[:max_chars]
        if len(log_output) > max_chars:
            trimmed += " ... [TRUNCATED_LOG_SNIPPET]"

        # Scrub potential credentials from log snippet
        scrubbed = re.sub(r"(token|bearer|key|secret)=([a-zA-Z0-9_\-\.]+)", r"\1=[REDACTED]", trimmed, flags=re.IGNORECASE)

        return {
            "snippet": scrubbed,
            "original_length": len(log_output),
            "is_truncated": len(log_output) > max_chars,
        }
