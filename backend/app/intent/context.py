"""Temporal context resolution using user-effective timezones and timestamps (Spec 18, 19, 20)."""

from datetime import UTC, datetime, timedelta
import logging
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger("kairo.intent.context")


class TemporalContextResolver:
    """Resolves relative temporal references into bounded timestamp ranges."""

    TEMPORAL_PATTERNS = {
        "yesterday": re.compile(r"\byesterday\b", re.IGNORECASE),
        "today": re.compile(r"\btoday\b", re.IGNORECASE),
        "this_morning": re.compile(r"\bthis\s+morning\b", re.IGNORECASE),
        "last_week": re.compile(r"\blast\s+week\b", re.IGNORECASE),
        "earlier": re.compile(r"\bearlier\b", re.IGNORECASE),
        "recently": re.compile(r"\b(recently|lately|what\s+happened\s+recently)\b", re.IGNORECASE),
    }

    @classmethod
    def resolve_temporal_range(
        cls,
        text: str,
        user_timezone: str = "UTC",
        now_dt: datetime | None = None,
    ) -> tuple[str | None, datetime | None, datetime | None]:
        """
        Extracts temporal keywords and computes exact (start_dt, end_dt) in UTC.
        INVARIANT: Uses the user's effective timezone to calculate calendar boundaries (Spec 19).
        """
        try:
            tz = ZoneInfo(user_timezone)
        except (ZoneInfoNotFoundError, ValueError, Exception):
            tz = ZoneInfo("UTC")

        now_utc = now_dt or datetime.now(UTC)
        now_local = now_utc.astimezone(tz)

        for keyword, pattern in cls.TEMPORAL_PATTERNS.items():
            if pattern.search(text):
                if keyword == "today":
                    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    return keyword, start_local.astimezone(UTC), now_utc

                elif keyword == "yesterday":
                    yest_local = now_local - timedelta(days=1)
                    start_local = yest_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_local = yest_local.replace(hour=23, minute=59, second=59, microsecond=999999)
                    return keyword, start_local.astimezone(UTC), end_local.astimezone(UTC)

                elif keyword == "this_morning":
                    start_local = now_local.replace(hour=6, minute=0, second=0, microsecond=0)
                    end_local = now_local.replace(hour=12, minute=0, second=0, microsecond=0)
                    return keyword, start_local.astimezone(UTC), end_local.astimezone(UTC)

                elif keyword == "last_week":
                    start_local = (now_local - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
                    return keyword, start_local.astimezone(UTC), now_utc

                elif keyword in ("earlier", "recently"):
                    start_local = now_local - timedelta(hours=6)
                    return keyword, start_local.astimezone(UTC), now_utc

        return None, None, None
