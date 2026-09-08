"""Trigger calculation, schedule evaluation, and timezone handling."""

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MIN_INTERVAL_SECONDS = 60


class TriggerValidationError(ValueError):
    """Raised when trigger configuration violates validation rules."""


def validate_timezone(tz_name: str | None) -> ZoneInfo:
    """Validate and return ZoneInfo object from IANA timezone string."""
    if not tz_name or not str(tz_name).strip():
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name.strip())
    except ZoneInfoNotFoundError as exc:
        raise TriggerValidationError(f"Invalid IANA timezone: '{tz_name}'") from exc


def calculate_next_run(
    trigger_config: dict[str, Any],
    from_time: datetime | None = None,
    min_interval_seconds: int = MIN_INTERVAL_SECONDS,
) -> datetime | None:
    """Calculate the next due UTC timestamp for a workflow trigger.

    Supports:
    - once: run once at specific time
    - hourly: run every hour at minute :00 (or minute specified)
    - daily: run every day at specified time (e.g. "08:00") in target timezone
    - weekly: run every week on day_of_week (0=Mon, 6=Sun) at specified time

    SECURITY:
    - Enforces minimum interval of 60 seconds.
    - Resolves all calculations in target timezone and returns normalized UTC datetime.
    """
    trigger_type = trigger_config.get("trigger_type")
    if trigger_type == "manual":
        return None

    tz = validate_timezone(trigger_config.get("timezone", "UTC"))
    now_utc = from_time if from_time is not None else datetime.now(UTC)
    now_local = now_utc.astimezone(tz)

    interval = trigger_config.get("interval", "daily")

    if interval == "hourly":
        # Next top of the hour (or current + 1 hour)
        candidate_local = now_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        # Ensure at least min_interval_seconds in future
        if (candidate_local.astimezone(UTC) - now_utc).total_seconds() < min_interval_seconds:
            candidate_local += timedelta(hours=1)
        return candidate_local.astimezone(UTC)

    time_str = trigger_config.get("time", "08:00") or "08:00"
    try:
        parts = [int(p.strip()) for p in time_str.split(":")]
        target_hour = parts[0]
        target_minute = parts[1] if len(parts) > 1 else 0
        if not (0 <= target_hour <= 23 and 0 <= target_minute <= 59):
            raise ValueError()
    except Exception as exc:
        raise TriggerValidationError(f"Invalid time format '{time_str}'. Expected 'HH:MM'.") from exc

    if interval == "daily":
        candidate_local = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if (
            candidate_local <= now_local
            or (candidate_local.astimezone(UTC) - now_utc).total_seconds() < min_interval_seconds
        ):
            candidate_local += timedelta(days=1)
        return candidate_local.astimezone(UTC)

    if interval == "weekly":
        target_day = int(trigger_config.get("day_of_week", 0))  # 0=Monday
        if not (0 <= target_day <= 6):
            raise TriggerValidationError(
                f"Invalid day_of_week '{target_day}'. Expected 0 (Monday) to 6 (Sunday)."
            )

        candidate_local = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        days_ahead = (target_day - now_local.weekday()) % 7
        candidate_local += timedelta(days=days_ahead)

        if (
            candidate_local <= now_local
            or (candidate_local.astimezone(UTC) - now_utc).total_seconds() < min_interval_seconds
        ):
            candidate_local += timedelta(days=7)

        return candidate_local.astimezone(UTC)

    if interval == "once":
        candidate_local = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if candidate_local <= now_local:
            return None
        return candidate_local.astimezone(UTC)

    return None
