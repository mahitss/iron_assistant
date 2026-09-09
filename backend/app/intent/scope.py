"""Target Scope Extraction, Resource Scoping, and Scope Ambiguity Detection (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kairo.intent.scope")


@dataclass
class IntentScope:
    """Bounded operational scope for an intent (Spec 43-45)."""

    project: Optional[str] = None
    environment: Optional[str] = None
    device: Optional[str] = None
    repository: Optional[str] = None
    service: Optional[str] = None
    data_resources: List[str] = field(default_factory=list)
    is_ambiguous: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project,
            "environment": self.environment,
            "device": self.device,
            "repository": self.repository,
            "service": self.service,
            "data_resources": self.data_resources,
            "is_ambiguous": self.is_ambiguous,
        }


class ScopeExtractor:
    """Extracts operational boundaries and flags ambiguous cross-resource scopes (Spec 43-45)."""

    ENV_PATTERNS = {
        "PRODUCTION": re.compile(r"\b(prod|production)\b", re.IGNORECASE),
        "STAGING": re.compile(r"\b(staging|stage)\b", re.IGNORECASE),
        "DEVELOPMENT": re.compile(r"\b(dev|development|local)\b", re.IGNORECASE),
    }

    @classmethod
    def extract_scope(
        cls,
        text: str,
        current_project: Optional[str] = None,
        current_env: Optional[str] = None,
    ) -> IntentScope:
        scope = IntentScope(
            project=current_project,
            environment=current_env or "DEVELOPMENT",
        )

        # Check explicit environment override
        for env_name, pat in cls.ENV_PATTERNS.items():
            if pat.search(text):
                scope.environment = env_name
                break

        # Check repository pattern
        m_repo = re.search(r"\b(?:in|on|repo|repository)\s+([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+)\b", text, re.IGNORECASE)
        if m_repo:
            scope.repository = m_repo.group(1).strip()

        # Check service pattern
        m_srv = re.search(r"\b(?:service|api)\s+([a-zA-Z0-9_\-]+)\b", text, re.IGNORECASE)
        if m_srv:
            scope.service = m_srv.group(1).strip()

        # Scope ambiguity check: e.g. "delete all databases across all projects"
        if "all projects" in text.lower() or "all services" in text.lower() or "everywhere" in text.lower():
            scope.is_ambiguous = True
            logger.warning("Scope ambiguity flagged: broad wildcard scope detected in '%s'", text)

        return scope
