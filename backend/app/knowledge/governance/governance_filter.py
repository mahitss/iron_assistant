"""Knowledge governance filter enforcing classification clearance, RBAC, and prompt injection defense."""

import logging
import re
from typing import Any

from app.knowledge.schemas import (
    ClassificationLevel,
    DocumentChunk,
    FreshnessState,
    QuarantineRecord,
    RetrievalResult,
)

logger = logging.getLogger("kairo.knowledge.governance")

# Injection and jailbreak detection patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?(system|initial)\s+prompt", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\bdan\s+mode\b", re.IGNORECASE),
    re.compile(r"bypass\s+(all\s+)?security\s+policies", re.IGNORECASE),
    re.compile(r"as\s+an\s+ai\s+without\s+restrictions", re.IGNORECASE),
    re.compile(r"reveal\s+your\s+secret\s+key", re.IGNORECASE),
]

CLASSIFICATION_HIERARCHY = {
    ClassificationLevel.PUBLIC: 1,
    ClassificationLevel.INTERNAL: 2,
    ClassificationLevel.CONFIDENTIAL: 3,
    ClassificationLevel.RESTRICTED: 4,
}

ROLE_CLEARANCE = {
    "guest": ClassificationLevel.PUBLIC,
    "user": ClassificationLevel.INTERNAL,
    "member": ClassificationLevel.CONFIDENTIAL,
    "admin": ClassificationLevel.RESTRICTED,
    "system": ClassificationLevel.RESTRICTED,
}


class KnowledgeGovernanceFilter:
    """Enforces policy clearances, confidentiality levels, and strips injected or poisoned chunks."""

    def __init__(self, policy_engine: Any | None = None) -> None:
        self.policy_engine = policy_engine
        self._quarantined: list[QuarantineRecord] = []

    def check_poisoning(self, content: str) -> tuple[bool, str | None]:
        """Scan text for prompt injection and adversarial manipulation patterns."""
        for pattern in PROMPT_INJECTION_PATTERNS:
            match = pattern.search(content)
            if match:
                return True, f"Matched injection pattern: '{match.group(0)}'"
        return False, None

    def filter_chunks(
        self,
        results: list[RetrievalResult],
        user_id: str,
        user_role: str = "member",
        user_clearance: ClassificationLevel | None = None,
        allow_stale: bool = True,
    ) -> list[RetrievalResult]:
        """Validate and filter candidate retrieval results according to classification, role, and integrity."""
        max_allowed_tier = user_clearance or ROLE_CLEARANCE.get(user_role.lower(), ClassificationLevel.INTERNAL)
        max_allowed_level = CLASSIFICATION_HIERARCHY.get(max_allowed_tier, 2)

        approved_results: list[RetrievalResult] = []

        for item in results:
            chunk = item.chunk
            meta = chunk.metadata

            # 1. Prompt Injection / Poisoning Check
            is_poisoned, reason = self.check_poisoning(chunk.content)
            if is_poisoned:
                logger.warning("Quarantining poisoned chunk %s: %s", chunk.id, reason)
                self._quarantined.append(
                    QuarantineRecord(
                        chunk_id=chunk.id,
                        document_id=meta.document_id,
                        reason=reason or "Detected prompt injection",
                        threat_type="PROMPT_INJECTION",
                        quarantined_by="KnowledgeGovernanceFilter",
                    )
                )
                continue

            # 2. Data Classification Clearance
            chunk_level = CLASSIFICATION_HIERARCHY.get(meta.classification, 1)
            if chunk_level > max_allowed_level:
                logger.debug(
                    "User %s with clearance %s denied access to chunk %s (%s)",
                    user_id,
                    max_allowed_tier.value,
                    chunk.id,
                    meta.classification.value,
                )
                continue

            # 3. Freshness Filter
            if not allow_stale and meta.freshness == FreshnessState.DEPRECATED:
                continue

            approved_results.append(item)

        return approved_results

    def get_quarantined_records(self) -> list[QuarantineRecord]:
        return list(self._quarantined)

    def clear_quarantined(self) -> None:
        self._quarantined.clear()
