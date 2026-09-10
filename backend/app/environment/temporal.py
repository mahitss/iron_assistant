"""Temporal utilities, freshness scoring, and as-of time validation (Task 54)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.environment.safety import FutureLeakageError
from app.environment.schemas import FreshnessState


def utc_now() -> datetime:
    """Returns authoritative current UTC timestamp."""
    return datetime.now(timezone.utc)


def parse_utc(dt_val: str | datetime | None) -> datetime:
    """Parses or normalizes a timestamp to timezone-aware UTC datetime."""
    if dt_val is None:
        return utc_now()
    if isinstance(dt_val, str):
        # handle ISO string
        dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
    else:
        dt = dt_val
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_freshness(
    last_seen: datetime | str,
    fresh_threshold_seconds: int = 300,   # 5 mins
    stale_threshold_seconds: int = 1800,  # 30 mins
    reference_time: datetime | None = None,
) -> FreshnessState:
    """Evaluates freshness of an observation against reference time."""
    ref = reference_time or utc_now()
    seen = parse_utc(last_seen)
    if seen > ref:
        return FreshnessState.FRESH
    age = (ref - seen).total_seconds()
    if age <= fresh_threshold_seconds:
        return FreshnessState.FRESH
    elif age <= stale_threshold_seconds:
        return FreshnessState.STALE
    else:
        return FreshnessState.EXPIRED


def validate_as_of(record_timestamp: datetime | str, as_of: datetime | str) -> bool:
    """Validates that a record timestamp was valid at the as-of moment without future leakage."""
    rec_time = parse_utc(record_timestamp)
    target_time = parse_utc(as_of)
    if rec_time > target_time:
        return False
    return True


def assert_no_future_leakage(query_as_of: datetime | str, observation_timestamp: datetime | str) -> None:
    """Enforces prompt #69, #207: Historical state must not use future observations."""
    q_time = parse_utc(query_as_of)
    o_time = parse_utc(observation_timestamp)
    if o_time > q_time:
        raise FutureLeakageError(
            f"Future leakage detected: observation time {o_time.isoformat()} is newer than query as_of {q_time.isoformat()}."
        )
