"""Entity Extraction, Multi-Class Recognition, and Safe Pronoun Resolution (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional

from app.intent.schemas import IntentEntity, ResolutionMethod

logger = logging.getLogger("kairo.intent.entities")


class EntityExtractor:
    """Extracts typed entities and resolves pronouns with consequential safety bounds (Spec 29-32, 161, 162)."""

    # Multi-class recognition patterns (Spec 29)
    PATTERNS = [
        ("FILE", re.compile(r"\b([a-zA-Z0-9_\-\./\\]+\.(?:py|js|ts|json|md|html|css|yaml|yml|sh|sql|pdf|txt|csv|log))\b", re.IGNORECASE)),
        ("REPOSITORY", re.compile(r"\b(?:repo|repository|github\.com/)?([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+)\b", re.IGNORECASE)),
        ("SERVICE", re.compile(r"\b(service:[a-zA-Z0-9_\-]+|[a-zA-Z0-9_\-]+(?:-api|-service)|redis|postgres|auth_service|payment_gateway|api_server)\b", re.IGNORECASE)),
        ("DEVICE", re.compile(r"\b(device:[a-zA-Z0-9_\-]+|desktop|phone|laptop|tablet|worker-node-\d+)\b", re.IGNORECASE)),
        ("PERSON", re.compile(r"(?:@([a-zA-Z0-9_\-]+)|\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b)", re.IGNORECASE)),
    ]

    PRONOUNS = {"it", "that", "them", "there", "this"}

    @classmethod
    def extract_entities(cls, text: str) -> List[IntentEntity]:
        entities: List[IntentEntity] = []

        for entity_type, regex in cls.PATTERNS:
            for match in regex.finditer(text):
                val = (match.group(1) or match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1)).strip()
                entities.append(
                    IntentEntity(
                        entity_type=entity_type.upper(),
                        name=val,
                        resolution_method=ResolutionMethod.EXPLICIT,
                        confidence=0.95,
                    )
                )

        return entities

    @classmethod
    def resolve_pronouns(
        cls,
        text: str,
        recent_entities: Optional[List[IntentEntity]] = None,
        is_destructive_action: bool = False,
        known_entities: Optional[List[IntentEntity]] = None,
    ) -> tuple[Optional[IntentEntity], bool]:
        """Enforce Spec 32, 111: Resolve 'it', 'that', 'this'.
        If action is destructive, NEVER guess ambiguous pronoun references!
        """
        candidates = recent_entities if recent_entities is not None else (known_entities or [])
        words = text.lower().split()
        contains_pronoun = any(p in words for p in cls.PRONOUNS)

        if not contains_pronoun:
            return None, False

        # If destructive action and ambiguous candidates exist -> DO NOT GUESS! (Spec 111)
        if is_destructive_action:
            if len(candidates) != 1:
                logger.warning("PRONOUN RESOLUTION BLOCKED on destructive action: candidates count=%d", len(candidates))
                return None, True  # Ambiguous! Must clarify

        if len(candidates) == 1:
            resolved = candidates[0]
            logger.info("Resolved pronoun to '%s' (%s)", resolved.name, resolved.entity_type)
            return resolved, False

        return None, len(candidates) > 1

