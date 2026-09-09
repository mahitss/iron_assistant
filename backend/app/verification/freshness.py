"""Freshness & Temporal Validity Engine for Kairo (Task 42).

Tracks observation timestamps, freshness windows (TTL), temporal decay,
and prevents stale evidence from asserting current state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.verification.claims import Claim, TruthStatus
from app.verification.evidence import Evidence, EvidenceType

logger = logging.getLogger("kairo.verification.freshness")

# Default TTL in seconds by domain or evidence type
DEFAULT_FRESHNESS_WINDOWS: dict[str, int] = {
    "server_health": 60,            # 1 minute
    "deployment_state": 180,        # 3 minutes
    "device_telemetry": 120,        # 2 minutes
    "git_head": 300,                # 5 minutes
    "api_response": 300,            # 5 minutes
    "tool_result": 300,             # 5 minutes
    "file_hash": 3600,              # 1 hour
    "database_schema": 3600,        # 1 hour
    "test_result": 900,             # 15 minutes
    "web_source": 86400,            # 24 hours
    "memory_reference": 86400 * 7,  # 7 days (historical context only)
    "default": 300,                 # 5 minutes fallback
}


@dataclass
class FreshnessEvaluation:
    """Result of evaluating claim or evidence temporal validity."""

    target_id: str
    target_type: str  # "claim" or "evidence"
    observed_at: datetime
    age_seconds: float
    freshness_window_seconds: float
    is_fresh: bool
    status: str  # "FRESH", "EXPIRING_SOON", "STALE", "EXPIRED"
    reason: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "observed_at": self.observed_at.isoformat(),
            "age_seconds": round(self.age_seconds, 2),
            "freshness_window_seconds": self.freshness_window_seconds,
            "is_fresh": self.is_fresh,
            "status": self.status,
            "reason": self.reason,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class FreshnessTracker:
    """Manages temporal validity windows and stale-state identification."""

    def __init__(self, custom_windows: dict[str, int] | None = None) -> None:
        self.windows = dict(DEFAULT_FRESHNESS_WINDOWS)
        if custom_windows:
            self.windows.update(custom_windows)

    def get_window(self, domain_or_type: str) -> int:
        """Retrieve freshness window in seconds for a given domain or evidence type."""
        clean_key = domain_or_type.lower().strip()
        return self.windows.get(clean_key, self.windows["default"])

    def evaluate_evidence(
        self,
        evidence: Evidence,
        as_of: datetime | None = None,
        max_age_seconds: int | None = None,
    ) -> FreshnessEvaluation:
        """Evaluate whether an evidence item is sufficiently fresh for current state."""
        as_of = as_of or datetime.now(timezone.utc)
        obs_time = evidence.observed_at
        if obs_time.tzinfo is None:
            obs_time = obs_time.replace(tzinfo=timezone.utc)

        age = (as_of - obs_time).total_seconds()
        
        window = max_age_seconds if max_age_seconds is not None else self.get_window(evidence.source_type.value)
        is_fresh = age <= window

        if age > window:
            status = "EXPIRED" if age > (window * 2) else "STALE"
            reason = f"Evidence age ({age:.1f}s) exceeds freshness window ({window}s)"
        elif age > (window * 0.8):
            status = "EXPIRING_SOON"
            reason = f"Evidence nearing expiration ({age:.1f}s / {window}s)"
        else:
            status = "FRESH"
            reason = f"Evidence within freshness window ({age:.1f}s <= {window}s)"

        return FreshnessEvaluation(
            target_id=evidence.evidence_id,
            target_type="evidence",
            observed_at=obs_time,
            age_seconds=max(0.0, age),
            freshness_window_seconds=float(window),
            is_fresh=is_fresh,
            status=status,
            reason=reason,
            evaluated_at=as_of,
        )

    def evaluate_claim(
        self,
        claim: Claim,
        as_of: datetime | None = None,
    ) -> FreshnessEvaluation:
        """Evaluate whether a claim is fresh or has become stale."""
        as_of = as_of or datetime.now(timezone.utc)
        obs_time = claim.observed_at or claim.created_at
        if obs_time.tzinfo is None:
            obs_time = obs_time.replace(tzinfo=timezone.utc)

        age = (as_of - obs_time).total_seconds()
        
        # Check explicit expires_at first
        if claim.expires_at is not None:
            exp_time = claim.expires_at
            if exp_time.tzinfo is None:
                exp_time = exp_time.replace(tzinfo=timezone.utc)
            window = (exp_time - obs_time).total_seconds()
            is_fresh = as_of < exp_time
        else:
            domain = claim.scope.get("domain", "default") if isinstance(claim.scope, dict) else "default"
            window = float(self.get_window(domain))
            is_fresh = age <= window

        if not is_fresh:
            status = "EXPIRED" if age > (window * 1.5) else "STALE"
            reason = f"Claim age ({age:.1f}s) exceeds freshness window ({window:.1f}s)"
        else:
            status = "FRESH"
            reason = f"Claim is fresh ({age:.1f}s <= {window:.1f}s)"

        return FreshnessEvaluation(
            target_id=claim.claim_id,
            target_type="claim",
            observed_at=obs_time,
            age_seconds=max(0.0, age),
            freshness_window_seconds=window,
            is_fresh=is_fresh,
            status=status,
            reason=reason,
            evaluated_at=as_of,
        )

    def mark_stale_if_expired(self, claim: Claim) -> Claim:
        """If claim freshness has lapsed, transitions claim status to STALE."""
        evaluation = self.evaluate_claim(claim)
        if not evaluation.is_fresh and claim.truth_status in [
            TruthStatus.VERIFIED,
            TruthStatus.SUPPORTED,
        ]:
            logger.info(
                "Claim %s transitioned to STALE: %s",
                claim.claim_id,
                evaluation.reason,
            )
            claim.truth_status = TruthStatus.STALE
        return claim
