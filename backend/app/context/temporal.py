"""Timezone-aware temporal reference resolution for context extraction."""

import re
import zoneinfo
from datetime import UTC, datetime, timedelta


class TemporalResolver:
    """Resolves natural-language temporal references into UTC timestamp ranges."""

    PATTERNS: list[tuple[re.Pattern, str]] = [
        (re.compile(r"\b(earlier today|today|this morning|this afternoon)\b", re.IGNORECASE), "today"),
        (re.compile(r"\byesterday\b", re.IGNORECASE), "yesterday"),
        (re.compile(r"\b(last week|past week)\b", re.IGNORECASE), "last_week"),
        (re.compile(r"\b(this week)\b", re.IGNORECASE), "this_week"),
        (re.compile(r"\b(recently|lately|recent)\b", re.IGNORECASE), "recently"),
        (re.compile(r"\b(last month|past month)\b", re.IGNORECASE), "last_month"),
    ]

    @classmethod
    def resolve_timezone(cls, tz_name: str | None) -> zoneinfo.ZoneInfo:
        """Safely load user timezone or fallback to UTC."""
        if not tz_name or not tz_name.strip():
            return zoneinfo.ZoneInfo("UTC")
        try:
            return zoneinfo.ZoneInfo(tz_name.strip())
        except Exception:
            return zoneinfo.ZoneInfo("UTC")

    @classmethod
    def extract_temporal_bounds(
        cls,
        text: str,
        timezone_name: str | None = "UTC",
        now_dt: datetime | None = None,
    ) -> tuple[datetime | None, datetime | None, str | None]:
        """Extract matched temporal token and return (start_utc, end_utc, label)."""
        if not text:
            return None, None, None

        tz = cls.resolve_timezone(timezone_name)
        now = (now_dt or datetime.now(UTC)).astimezone(tz)

        for pat, label in cls.PATTERNS:
            if pat.search(text):
                if label == "today":
                    start_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    return start_local.astimezone(UTC), now.astimezone(UTC), label

                if label == "yesterday":
                    yesterday_local = now - timedelta(days=1)
                    start_local = yesterday_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_local = yesterday_local.replace(hour=23, minute=59, second=59, microsecond=999999)
                    return start_local.astimezone(UTC), end_local.astimezone(UTC), label

                if label == "last_week":
                    start_local = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
                    return start_local.astimezone(UTC), now.astimezone(UTC), label

                if label == "this_week":
                    days_since_monday = now.weekday()
                    start_local = (now - timedelta(days=days_since_monday)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    return start_local.astimezone(UTC), now.astimezone(UTC), label

                if label == "recently":
                    start_local = now - timedelta(days=3)
                    return start_local.astimezone(UTC), now.astimezone(UTC), label

                if label == "last_month":
                    start_local = now - timedelta(days=30)
                    return start_local.astimezone(UTC), now.astimezone(UTC), label

        return None, None, None
