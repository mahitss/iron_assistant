"""Privacy preservation, log secret redaction, prompt injection guards, and data minimization (Task 55)."""

from __future__ import annotations

import re
from typing import Any

from app.causal.safety import CausalPoisoningError, CausalSafetyGuard
from app.causal.schemas import CausalEvidence

# Prompt #147: Prevent prompt injections from injecting causal conclusions
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|above|all)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+must\s+declare\s+(.*)\s+as\s+(the\s+)?root\s+cause", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:\s*", re.IGNORECASE),
    re.compile(r"override\s+causal\s+(engine|graph|verification)", re.IGNORECASE),
    re.compile(r"bypass\s+policy", re.IGNORECASE),
]


class CausalPrivacyEngine:
    """Safeguards privacy and blocks causal graph poisoning or injection attacks."""

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Prompt #144: Scrub secrets and credentials from logs or narrative text."""
        return CausalSafetyGuard.scrub_text(text)

    @staticmethod
    def check_injection_and_poisoning(text: str, source: str) -> None:
        """Prompt #146, #147: Detect attempts to poison causal assertions or inject prompts."""
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                raise CausalPoisoningError(
                    f"Blocked causal poisoning / prompt injection from source '{source}': pattern '{pattern.pattern}' detected."
                )

    @staticmethod
    def enforce_data_minimization(
        evidence_list: list[CausalEvidence],
        allowed_keys: set[str] | None = None,
    ) -> list[CausalEvidence]:
        """Prompt #142, #143: Keep only essential evidence payload fields to minimize sensitive data exposure."""
        keys = allowed_keys or {"service", "metric", "timestamp", "value", "threshold", "status", "error_code"}
        minimized = []

        for ev in evidence_list:
            filtered_obs: dict[str, Any] = {}
            for k, v in ev.observation.items():
                if k in keys:
                    if isinstance(v, str):
                        filtered_obs[k] = CausalSafetyGuard.scrub_text(v)
                    else:
                        filtered_obs[k] = v

            ev_copy = ev.model_copy(deep=True)
            ev_copy.observation = filtered_obs
            minimized.append(ev_copy)

        return minimized
