"""Privacy controls and context isolation for Strategic Planning (Task 58)."""

from __future__ import annotations

import re
from typing import Any


class PlanningPrivacyManager:
    """Enforces least-data disclosure and scrubs personal identification from plans."""

    _EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    _IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

    def mask_plan_text(self, text: str) -> str:
        """Mask emails and IP addresses in plan strings."""
        if not isinstance(text, str):
            return str(text)
        masked = self._EMAIL_RE.sub("[MASKED_EMAIL]", text)
        masked = self._IP_RE.sub("[MASKED_IP]", masked)
        return masked

    def sanitize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Scrubs PII and exposes only project-scope relevant context."""
        cleaned: dict[str, Any] = {}
        for k, v in context.items():
            if k in {"personal_notes", "private_messages", "unrelated_credentials"}:
                continue
            cleaned[k] = self._mask_pii(v)
        return cleaned

    def _mask_pii(self, val: Any) -> Any:
        if isinstance(val, str):
            return self.mask_plan_text(val)
        elif isinstance(val, dict):
            return {k: self._mask_pii(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._mask_pii(i) for i in val]
        return val


planning_privacy_manager = PlanningPrivacyManager()
