"""Privacy controls, least-data filtering, and sensitive context minimization for decisions."""

from __future__ import annotations

import copy
import re
from typing import Any

from app.decision.safety import scrub_decision_secrets

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
IPV4_PATTERN = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")


class DecisionPrivacyManager:
    """Applies least-data minimization and sanitization to decision contexts and logs."""

    def sanitize_context(self, context_dict: dict[str, Any]) -> dict[str, Any]:
        """Scrubs credentials, redacts private network addresses and emails, leaving minimal operational context."""
        cleaned = scrub_decision_secrets(copy.deepcopy(context_dict))
        return self._mask_pii(cleaned)

    def _mask_pii(self, data: Any) -> Any:
        if isinstance(data, str):
            masked = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", data)
            return masked
        elif isinstance(data, dict):
            return {k: self._mask_pii(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._mask_pii(x) for x in data]
        return data


privacy_manager = DecisionPrivacyManager()
