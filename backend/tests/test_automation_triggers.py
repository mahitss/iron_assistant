"""Unit tests for trigger schedule calculations, timezones, and intervals."""

from datetime import UTC, datetime

import pytest

from app.automation.triggers import (
    TriggerValidationError,
    calculate_next_run,
    validate_timezone,
)


def test_validate_timezone_valid_and_invalid():
    """Verify IANA timezone validation."""
    tz_utc = validate_timezone("UTC")
    assert str(tz_utc) == "UTC"

    tz_kolkata = validate_timezone("Asia/Kolkata")
    assert str(tz_kolkata) == "Asia/Kolkata"

    with pytest.raises(TriggerValidationError):
        validate_timezone("Invalid/Nonexistent_Timezone")


def test_schedule_daily():
    """Verify daily schedule in specified timezone."""
    # From 07:00 UTC, next daily at 08:00 UTC should be today at 08:00
    from_time = datetime(2026, 9, 8, 7, 0, 0, tzinfo=UTC)
    config = {
        "trigger_type": "schedule",
        "interval": "daily",
        "time": "08:00",
        "timezone": "UTC",
    }
    next_run = calculate_next_run(config, from_time=from_time)
    assert next_run == datetime(2026, 9, 8, 8, 0, 0, tzinfo=UTC)

    # From 09:00 UTC, next daily at 08:00 UTC should be tomorrow at 08:00
    from_time_after = datetime(2026, 9, 8, 9, 0, 0, tzinfo=UTC)
    next_run_after = calculate_next_run(config, from_time=from_time_after)
    assert next_run_after == datetime(2026, 9, 9, 8, 0, 0, tzinfo=UTC)


def test_schedule_hourly():
    """Verify hourly schedule advances to top of the next hour."""
    from_time = datetime(2026, 9, 8, 14, 25, 0, tzinfo=UTC)
    config = {
        "trigger_type": "schedule",
        "interval": "hourly",
        "timezone": "UTC",
    }
    next_run = calculate_next_run(config, from_time=from_time)
    assert next_run == datetime(2026, 9, 8, 15, 0, 0, tzinfo=UTC)


def test_schedule_weekly():
    """Verify weekly schedule calculates target day of the week."""
    # 2026-09-08 is a Tuesday (weekday=1)
    from_time = datetime(2026, 9, 8, 10, 0, 0, tzinfo=UTC)
    config = {
        "trigger_type": "schedule",
        "interval": "weekly",
        "day_of_week": 0,  # Monday
        "time": "09:00",
        "timezone": "UTC",
    }
    next_run = calculate_next_run(config, from_time=from_time)
    # Next Monday is 2026-09-14
    assert next_run.date().isoformat() == "2026-09-14"
    assert next_run.hour == 9
    assert next_run.minute == 0


def test_minimum_interval_enforcement():
    """Verify schedule within 60s is pushed to next interval."""
    # 07:59:45 UTC looking for 08:00 is only 15 seconds away (< 60s minimum interval)
    from_time = datetime(2026, 9, 8, 7, 59, 45, tzinfo=UTC)
    config = {
        "trigger_type": "schedule",
        "interval": "daily",
        "time": "08:00",
        "timezone": "UTC",
    }
    next_run = calculate_next_run(config, from_time=from_time, min_interval_seconds=60)
    # Should push to tomorrow
    assert next_run == datetime(2026, 9, 9, 8, 0, 0, tzinfo=UTC)
