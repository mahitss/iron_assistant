"""Multi-Intent Decomposition Engine for Task 108.

Supports requests containing multiple objectives (Spec 6).
Example:
"Analyze this repo, fix the bugs, run tests, and prepare a PR."
Decomposes into:
Intent 1: Analyze
Intent 2: Modify / Fix (depends on 1)
Intent 3: Validate / Run tests (depends on 2)
Intent 4: Prepare artifact / PR (depends on 3)

Preserves dependencies and priorities without collapsing everything into a vague blob.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.intent.domain import (
    EpistemicStatus,
    ExternalEffectFlag,
    Intent,
    IntentCategory,
    IntentPriorityLevel,
    RequestStatus,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.intent.decomposition")


class DecompositionEngine:
    """Decomposes compound user requests into structured, dependent intent nodes."""

    _CONJUNCTION_PATTERNS = [
        re.compile(r"\b(?:and\s+then|then|after\s+that|followed\s+by|next)\b", re.IGNORECASE),
        re.compile(r"\b(?:,\s*and\s+|\s+and\s+also\s+|\s+as\s+well\s+as\s+)\b", re.IGNORECASE),
        re.compile(r"\b(?:first|secondly|thirdly|finally)\b", re.IGNORECASE),
    ]

    _INTENT_KEYWORD_MAP: List[Tuple[re.Pattern, IntentCategory, str]] = [
        (re.compile(r"\b(?:analyze|inspect|examine|audit|investigate|review)\b", re.IGNORECASE), IntentCategory.ANALYSIS, "analyze"),
        (re.compile(r"\b(?:fix|repair|patch|resolve|refactor|update|edit|modify)\b", re.IGNORECASE), IntentCategory.MODIFICATION, "modify"),
        (re.compile(r"\b(?:test|validate|verify|check|benchmark)\b", re.IGNORECASE), IntentCategory.ANALYSIS, "validate"),
        (re.compile(r"\b(?:create|generate|write|author|build|scaffold|prepare\s+a\s+pr|open\s+a\s+pr)\b", re.IGNORECASE), IntentCategory.CREATION, "create"),
        (re.compile(r"\b(?:deploy|publish|release|push\s+to)\b", re.IGNORECASE), IntentCategory.AUTOMATION, "deploy"),
        (re.compile(r"\b(?:monitor|watch|observe|track)\b", re.IGNORECASE), IntentCategory.MONITORING, "monitor"),
        (re.compile(r"\b(?:optimize|speed\s+up|accelerate|streamline)\b", re.IGNORECASE), IntentCategory.OPTIMIZATION, "optimize"),
        (re.compile(r"\b(?:clean|clean\s+up|prune|remove|delete)\b", re.IGNORECASE), IntentCategory.MAINTENANCE, "clean"),
        (re.compile(r"\b(?:email|notify|message|post|send)\b", re.IGNORECASE), IntentCategory.COMMUNICATION, "communicate"),
        (re.compile(r"\b(?:debug|troubleshoot|diagnose)\b", re.IGNORECASE), IntentCategory.DEBUGGING, "debug"),
        (re.compile(r"\b(?:search|find|locate|lookup)\b", re.IGNORECASE), IntentCategory.RESEARCH, "search"),
        (re.compile(r"\b(?:compare|diff|contrast)\b", re.IGNORECASE), IntentCategory.COMPARISON, "compare"),
        (re.compile(r"\b(?:plan|schedule|orchestrate)\b", re.IGNORECASE), IntentCategory.PLANNING, "plan"),
        (re.compile(r"\b(?:stop|cancel|abort|halt|nevermind|never\s+mind)\b", re.IGNORECASE), IntentCategory.CONTROL, "cancel"),
    ]

    @classmethod
    def split_clauses(cls, text: str) -> List[str]:
        """Splits multi-action sentences into sequential clauses."""
        text = text.strip()
        if not text:
            return []

        # Split on sequential connectors: "and then", "then", "after that", etc.
        pattern = r"(?:\s*;\s*|\s*\.\s+|\s+and\s+then\s+|\s+then\s+|\s+after\s+that\s+|\s*,\s*and\s+|\s*,\s*(?=(?:fix|run|prepare|test|deploy|build|analyze|clean)\b))"
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        clauses = [p.strip() for p in parts if p.strip()]
        return clauses if clauses else [text]

    @classmethod
    def classify_clause(cls, clause: str) -> Tuple[IntentCategory, str]:
        """Classifies a clause into category and primary action label."""
        for pat, cat, action in cls._INTENT_KEYWORD_MAP:
            if pat.search(clause):
                return cat, action

        # Default fallback
        if "?" in clause or clause.lower().startswith(("how", "what", "where", "why", "when", "can you")):
            return IntentCategory.INFORMATION, "query"
        return IntentCategory.CREATION, "execute"

    @classmethod
    def extract_target(cls, clause: str) -> Tuple[str, EpistemicStatus]:
        """Extracts the direct target of the clause."""
        patterns = [
            re.compile(r"\b(?:this|the|my)\s+([a-zA-Z0-9_\-\./]+(?:\s+[a-zA-Z0-9_\-\.]+)?)\b", re.IGNORECASE),
            re.compile(r"\b(?:repo|repository|database|api|backend|frontend|server|deployment|test|tests|pr|pull\s+request|folder|directory|file)\b", re.IGNORECASE),
        ]
        for pat in patterns:
            match = pat.search(clause)
            if match:
                val = match.group(0).strip()
                return val, EpistemicStatus.EXPLICIT

        # Check for vague target indicators
        if any(w in clause.lower() for w in ["it", "them", "those", "that", "something", "everything"]):
            return "UNKNOWN", EpistemicStatus.UNKNOWN

        return "UNKNOWN", EpistemicStatus.UNKNOWN

    @classmethod
    def flag_external_effect(cls, category: IntentCategory, clause: str) -> ExternalEffectFlag:
        """Determines if the clause carries potential external effects."""
        external_keywords = ["email", "message", "post", "tweet", "publish", "deploy", "delete", "purchase", "pay", "charge", "external"]
        if category in (IntentCategory.COMMUNICATION, IntentCategory.AUTOMATION):
            return ExternalEffectFlag.EXTERNAL_EFFECT_POSSIBLE
        if any(w in clause.lower() for w in external_keywords):
            return ExternalEffectFlag.EXTERNAL_EFFECT_POSSIBLE
        return ExternalEffectFlag.INTERNAL_ONLY

    @classmethod
    def decompose(cls, request_id: str, raw_text: str) -> List[Intent]:
        """Decomposes a raw request into a DAG of linked structured intents."""
        clauses = cls.split_clauses(raw_text)
        intents: List[Intent] = []
        prior_intent_id: Optional[str] = None

        for idx, clause in enumerate(clauses):
            cat, action_class = cls.classify_clause(clause)
            target, target_epistemic = cls.extract_target(clause)
            external_effect = cls.flag_external_effect(cat, clause)

            dependencies = [prior_intent_id] if prior_intent_id else []

            intent = Intent(
                intent_id=generate_id(f"int_{idx+1}"),
                request_id=request_id,
                parent_intent_id=None if idx == 0 else intents[0].intent_id,
                dependency_ids=dependencies,
                category=cat,
                action_class=action_class,
                target=target,
                target_epistemic=target_epistemic,
                summary=clause,
                user_visible_outcome=f"Successfully complete: {clause}",
                external_effect=external_effect,
                priority=IntentPriorityLevel.NORMAL,
                target_confidence=0.9 if target != "UNKNOWN" else 0.4,
                goal_confidence=0.85,
                constraint_confidence=0.9,
                overall_confidence=0.85 if target != "UNKNOWN" else 0.5,
                status=RequestStatus.UNDERSTOOD,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            intents.append(intent)
            prior_intent_id = intent.intent_id

        logger.info("Decomposed request %s into %d structured intent(s)", request_id, len(intents))
        return intents

    @classmethod
    def decompose_request(cls, raw_text: str, request_id: str = "req_default", **kwargs: Any) -> List[Intent]:
        """Convenience alias for request decomposition."""
        return cls.decompose(request_id=request_id, raw_text=raw_text)
