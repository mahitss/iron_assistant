"""Command classification using deterministic rules first, with ModelRouter fallback (Spec 5, 50, 51, 52)."""

import logging
import re
from typing import Any

from app.intent.schemas import IntentType

logger = logging.getLogger("kairo.intent.classifier")


class CommandClassifier:
    """Classifies user commands into structured intent types with deterministic priority."""

    # Deterministic regex patterns for high-frequency or safety-critical commands
    PATTERNS: list[tuple[IntentType, list[re.Pattern]]] = [
        # APPROVE / REJECT
        (
            IntentType.APPROVE,
            [
                re.compile(r"^(approve|confirm|authorize|lgtm|accept)(\s+it|\s+the|\s+this)?\b", re.IGNORECASE),
                re.compile(r"^(yes|yep|proceed|go\s+ahead)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.REJECT,
            [
                re.compile(r"^(reject|deny|disapprove|block)(\s+it|\s+the|\s+this)?\b", re.IGNORECASE),
                re.compile(r"^(no|don't\s+do\s+it|abort\s+approval)\b", re.IGNORECASE),
            ],
        ),
        # CANCEL / PAUSE / RESUME / RETRY
        (
            IntentType.CANCEL,
            [
                re.compile(r"^(cancel|stop|abort|kill|halt)(\s+the|\s+that|\s+this|\s+all)?(\s+task|\s+job|\s+operation|\s+it)?\b", re.IGNORECASE),
                re.compile(r"^stop\s+it\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.PAUSE,
            [
                re.compile(r"^(pause|freeze|hold\s+on|suspend)(\s+the|\s+that|\s+this)?(\s+task|\s+job|\s+it)?\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.RESUME,
            [
                re.compile(r"^(resume|unpause)(\s+the|\s+that|\s+this)?(\s+task|\s+job|\s+it)?\b", re.IGNORECASE),
                re.compile(r"^continue(\s+the\s+task|\s+task|\s+it)?$", re.IGNORECASE),
            ],
        ),
        (
            IntentType.RETRY,
            [
                re.compile(r"^(retry|try\s+again|rerun|re-run)(\s+the|\s+that|\s+this)?(\s+task|\s+job|\s+it)?\b", re.IGNORECASE),
                re.compile(r"^do\s+that\s+again\b", re.IGNORECASE),
                re.compile(r"^do\s+the\s+same\s+thing\s+again\b", re.IGNORECASE),
            ],
        ),
        # AUTOMATE / REMIND
        (
            IntentType.AUTOMATE,
            [
                re.compile(r"\b(every\s+(morning|day|week|month|hour|minute)|schedule|cron|run\s+daily)\b", re.IGNORECASE),
                re.compile(r"^automate\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.REMIND,
            [
                re.compile(r"^(remind\s+me|set\s+a?\s*reminder)\b", re.IGNORECASE),
            ],
        ),
        # SUMMARIZE / COMPARE / EXPLAIN / ANALYZE
        (
            IntentType.SUMMARIZE,
            [
                re.compile(r"^(summarize|give\s+me\s+a\s+summary|tldr|tl;dr)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.COMPARE,
            [
                re.compile(r"^(compare|diff|show\s+differences)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.EXPLAIN,
            [
                re.compile(r"^(explain|what\s+does\s+this\s+(mean|do)|walk\s+me\s+through)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.ANALYZE,
            [
                re.compile(r"^(analyze|inspect|audit|evaluate|diagnose|review)\b", re.IGNORECASE),
                re.compile(r"^what'?s\s+wrong\s+with\s+(this|it|my)\b", re.IGNORECASE),
            ],
        ),
        # SEARCH / NAVIGATE
        (
            IntentType.SEARCH,
            [
                re.compile(r"^(find|search|lookup|look\s+for|where\s+is)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.NAVIGATE,
            [
                re.compile(r"^(open|navigate\s+to|go\s+to|view|show\s+me)\b.*?\b(page|tab|dashboard|settings|view|repo|commit|pr|pull\s+request)\b", re.IGNORECASE),
            ],
        ),
        # MUTATIONS: DELETE / UPDATE / CREATE / MODIFY / CODE / DEPLOY
        (
            IntentType.DELETE,
            [
                re.compile(r"^(delete|remove|erase|destroy|drop|wipe|purge)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.DEPLOY,
            [
                re.compile(r"^(deploy|ship|release|rollout|push\s+to\s+production|push\s+to\s+staging)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.CODE,
            [
                re.compile(r"^(write\s+code|code|implement|refactor|scaffold|program)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.DEBUG,
            [
                re.compile(r"^(debug|troubleshoot|trace\s+bug|fix\s+bug|find\s+error)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.COMMUNICATE,
            [
                re.compile(r"^(message|email|send\s+message|slack|dm|chat)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.NOTIFY,
            [
                re.compile(r"^(notify|alert|ping\s+me|tell\s+me\s+when)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.MONITOR,
            [
                re.compile(r"^(monitor|watch|track|keep\s+an\s+eye\s+on)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.SCHEDULE,
            [
                re.compile(r"^(schedule|set\s+schedule|run\s+at)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.TRANSACT,
            [
                re.compile(r"^(buy|pay|purchase|transact|transfer\s+funds)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.RESEARCH,
            [
                re.compile(r"^(research|deep\s+dive|investigate\s+topic)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.PLAN,
            [
                re.compile(r"^(plan|draft\s+plan|create\s+plan|plan\s+out)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.MODIFY,
            [
                re.compile(r"^(modify|tweak|adjust|change|alter)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.UPDATE,
            [
                re.compile(r"^(update|modify|change|edit|patch|rename|set)\b", re.IGNORECASE),
            ],
        ),
        (
            IntentType.CREATE,
            [
                re.compile(r"^(create|generate|add|build|make|new|write)\b", re.IGNORECASE),
            ],
        ),
        # AUTONOMOUS TASK / DEPLOYMENT / INVESTIGATION
        (
            IntentType.TASK,
            [
                re.compile(r"\b(investigate|fix|resolve|debug|deploy|build|patch|refactor|benchmark)\b", re.IGNORECASE),
                re.compile(r"^fix\s+the\s+(ci|test|build|bug|issue)\b", re.IGNORECASE),
                re.compile(r"^deploy(\s+it|\s+to|\s+the)?\b", re.IGNORECASE),
            ],
        ),
        # QUESTION (General conversational query)
        (
            IntentType.QUESTION,
            [
                re.compile(r"^(what|why|how|when|who|is\s+there|can\s+you|are\s+you|tell\s+me)\b", re.IGNORECASE),
            ],
        ),
    ]

    @classmethod
    def classify(cls, text: str, attachments: list[Any] | None = None) -> IntentType:
        """Deterministically classify text into an IntentType, with media contextual awareness."""
        clean = text.strip()

        # Check attachment hints: if "what's wrong with this" + image -> ANALYZE
        if attachments and len(attachments) > 0:
            if re.search(r"\b(what'?s\s+wrong|look\s+at\s+this|explain\s+this|inspect)\b", clean, re.IGNORECASE):
                return IntentType.ANALYZE
            if re.search(r"\b(summarize)\b", clean, re.IGNORECASE):
                return IntentType.SUMMARIZE

        # Check deterministic patterns
        for intent_type, regex_list in cls.PATTERNS:
            for pattern in regex_list:
                if pattern.search(clean):
                    return intent_type

        # Default fallback: If it ends with '?', treat as QUESTION; otherwise REQUEST
        if clean.endswith("?"):
            return IntentType.QUESTION

        return IntentType.REQUEST

    @classmethod
    def classify_deterministic(cls, text: str) -> IntentType:
        """Deterministic classification entrypoint for multi-intent clause parsing."""
        return cls.classify(text)

