"""Temporal ordering, interval checks, and causal decay utilities (Task 55, Prompts #7, #8, #92, #170)."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Returns authoritative timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def parse_utc(val: datetime | str | None) -> datetime:
    """Normalizes ISO string or datetime to timezone-aware UTC datetime."""
    if val is None:
        return utc_now()
    if isinstance(val, str):
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
    else:
        dt = val
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_temporally_prior(time_a: datetime | str, time_b: datetime | str) -> bool:
    """Prompt #7: Checks if event A strictly occurred before event B."""
    a = parse_utc(time_a)
    b = parse_utc(time_b)
    return a < b


def calculate_temporal_distance_seconds(time_a: datetime | str, time_b: datetime | str) -> float:
    """Computes duration in seconds between two timestamps."""
    a = parse_utc(time_a)
    b = parse_utc(time_b)
    return abs((b - a).total_seconds())


def evaluate_causal_decay(
    established_at: datetime | str,
    half_life_days: int = 30,
    current_time: datetime | None = None,
) -> float:
    """Prompt #92, #170: Computes time-decay multiplier [0.0 - 1.0] for causal memory."""
    now = current_time or utc_now()
    est = parse_utc(established_at)
    if est > now:
        return 1.0
    age_days = (now - est).total_seconds() / 86400.0
    # Exponential decay: 0.5 ** (age / half_life)
    decay = 0.5 ** (age_days / half_life_days)
    return round(max(0.1, min(1.0, decay)), 3)
