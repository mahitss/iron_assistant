"""Context Integration, Temporal Normalization, and Staleness Detection (Tasks 35 & 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
import logging
import re
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger("kairo.intent.context")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ContextSnapshot:
    """Integrated context from multiple subsystems (Spec 25-28).
    
    CRITICAL INVARIANT (Spec 26):
    Context provides interpretation. It does NOT automatically provide authorization!
    """

    user_id: str
    project_id: Optional[str] = None
    conversation_id: Optional[str] = None
    recent_task_id: Optional[str] = None
    environment: str = "DEVELOPMENT"
    active_entities: List[Dict[str, Any]] = field(default_factory=list)
    memory_references: List[str] = field(default_factory=list)
    captured_at: datetime = field(default_factory=utc_now)
    ttl_seconds: float = 3600.0

    @property
    def is_stale(self) -> bool:
        """Enforce Spec 28: Mark stale context."""
        return (utc_now() - self.captured_at).total_seconds() > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "project_id": self.project_id,
            "conversation_id": self.conversation_id,
            "recent_task_id": self.recent_task_id,
            "environment": self.environment,
            "active_entities": self.active_entities,
            "memory_references": self.memory_references,
            "is_stale": self.is_stale,
            "captured_at": self.captured_at.isoformat(),
        }


class IntentContextManager:
    """Retrieves relevant context for intent disambiguation while guarding against authorization leakage (Spec 25-28)."""

    def __init__(self) -> None:
        # conversation_id -> ContextSnapshot
        self._conversations: Dict[str, ContextSnapshot] = {}

    def capture_context(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        recent_task_id: Optional[str] = None,
        environment: str = "DEVELOPMENT",
        active_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> ContextSnapshot:
        cid = conversation_id or f"conv_{user_id}"
        snap = ContextSnapshot(
            user_id=user_id,
            project_id=project_id,
            conversation_id=cid,
            recent_task_id=recent_task_id,
            environment=environment,
            active_entities=active_entities or [],
            captured_at=utc_now(),
        )
        self._conversations[cid] = snap
        return snap

    def get_context(self, conversation_id: str) -> Optional[ContextSnapshot]:
        snap = self._conversations.get(conversation_id)
        if snap and snap.is_stale:
            logger.info("Context snapshot for conversation %s is stale (>ttl)", conversation_id)
        return snap


class TemporalContextResolver:
    """Resolves relative temporal references into bounded timestamp ranges (Spec 18-20, 33-36)."""

    TEMPORAL_PATTERNS = {
        "yesterday": re.compile(r"\byesterday\b", re.IGNORECASE),
        "today": re.compile(r"\btoday\b", re.IGNORECASE),
        "tomorrow": re.compile(r"\btomorrow\b", re.IGNORECASE),
        "this_morning": re.compile(r"\bthis\s+morning\b", re.IGNORECASE),
        "last_week": re.compile(r"\blast\s+week\b", re.IGNORECASE),
        "next_week": re.compile(r"\bnext\s+week\b", re.IGNORECASE),
        "earlier": re.compile(r"\bearlier\b", re.IGNORECASE),
        "recently": re.compile(r"\b(recently|lately|what\s+happened\s+recently)\b", re.IGNORECASE),
        "soon": re.compile(r"\bsoon\b", re.IGNORECASE),
    }

    @classmethod
    def resolve_temporal_range(
        cls,
        text: str,
        user_timezone: str = "UTC",
        now_dt: Optional[datetime] = None,
    ) -> tuple[Optional[str], Optional[datetime], Optional[datetime]]:
        """Extracts temporal keywords and computes exact (start_dt, end_dt) in UTC."""
        try:
            tz = ZoneInfo(user_timezone)
        except (ZoneInfoNotFoundError, ValueError, Exception):
            tz = ZoneInfo("UTC")

        now_utc = now_dt or datetime.now(timezone.utc)
        now_local = now_utc.astimezone(tz)

        for keyword, pattern in cls.TEMPORAL_PATTERNS.items():
            if pattern.search(text):
                if keyword == "today":
                    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    return keyword, start_local.astimezone(timezone.utc), now_utc

                elif keyword == "tomorrow":
                    tom_local = now_local + timedelta(days=1)
                    start_local = tom_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_local = tom_local.replace(hour=23, minute=59, second=59, microsecond=999999)
                    return keyword, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

                elif keyword == "yesterday":
                    yest_local = now_local - timedelta(days=1)
                    start_local = yest_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_local = yest_local.replace(hour=23, minute=59, second=59, microsecond=999999)
                    return keyword, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

                elif keyword == "this_morning":
                    start_local = now_local.replace(hour=6, minute=0, second=0, microsecond=0)
                    end_local = now_local.replace(hour=12, minute=0, second=0, microsecond=0)
                    return keyword, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

                elif keyword == "last_week":
                    start_local = (now_local - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
                    return keyword, start_local.astimezone(timezone.utc), now_utc

                elif keyword == "next_week":
                    start_local = (now_local + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
                    end_local = (now_local + timedelta(days=14)).replace(hour=23, minute=59, second=59, microsecond=999999)
                    return keyword, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

                elif keyword in ("earlier", "recently", "soon"):
                    start_local = now_local - timedelta(hours=6)
                    return keyword, start_local.astimezone(timezone.utc), now_utc

        return None, None, None

    @classmethod
    def resolve_relative_time(
        cls,
        phrase: str,
        base_time: Optional[datetime] = None,
        user_timezone: str = "UTC",
    ) -> datetime:
        """Enforce Spec 33, 34: Resolve relative temporal expressions into concrete datetime."""
        ref = base_time or datetime.now(timezone.utc)
        clean = phrase.lower().strip()
        if "today" in clean:
            return ref
        elif "tomorrow" in clean:
            return ref + timedelta(days=1)
        elif "yesterday" in clean:
            return ref - timedelta(days=1)
        elif "next week" in clean:
            return ref + timedelta(days=7)
        elif "last week" in clean:
            return ref - timedelta(days=7)
        return ref

    @classmethod
    def is_flexible_time(cls, phrase: str) -> bool:
        """Enforce Spec 36: Preserve flexible semantics; do NOT invent exact time when user said 'morning'."""
        clean = phrase.lower()
        flexible_keywords = ["morning", "afternoon", "evening", "soon", "later", "before deployment", "after lunch"]
        return any(k in clean for k in flexible_keywords)

    @classmethod
    def convert_to_timezone(cls, dt: datetime, tz_name: str) -> datetime:
        """Enforce Spec 35: Convert datetime to user or project timezone."""
        try:
            target_tz = ZoneInfo(tz_name)
        except Exception:
            target_tz = ZoneInfo("UTC")
        return dt.astimezone(target_tz)

