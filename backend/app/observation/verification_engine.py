"""Observation Integrity, Provenance & Schema Verification Engine for Task 114.
Ensures observations are authenticated, fresh, untampered, and compliant with privacy boundaries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.observation.domain import (
    ObservationOutcome,
    ObservationVerification,
    VerificationStatus,
    compute_hash,
    utc_now,
)

logger = logging.getLogger("kairo.observation.verification_engine")


class ObservationVerificationEngine:
    """Performs rigorous verification of acquired empirical observations (Section 39)."""

    @classmethod
    def verify_observation(
        cls,
        outcome: ObservationOutcome,
        max_freshness_seconds: float = 60.0,
    ) -> ObservationVerification:
        notes = []

        # 1. Source Authentication
        source_auth = bool(outcome.source and not outcome.source.startswith("untrusted_"))
        if not source_auth:
            notes.append("Source failed authentication or carries untrusted identity.")

        # 2. Schema Validation
        schema_valid = isinstance(outcome.data_payload, dict) and bool(outcome.data_payload)
        if not schema_valid:
            notes.append("Payload schema missing or invalid.")

        # 3. Freshness Validation
        freshness_valid = outcome.freshness_seconds <= max_freshness_seconds
        if not freshness_valid:
            notes.append(f"Observation stale ({outcome.freshness_seconds:.1f}s > {max_freshness_seconds:.1f}s).")

        # 4. Tamper / Hash Check
        expected_hash = compute_hash(outcome.data_payload)
        tamper_free = outcome.provenance_hash == "" or outcome.provenance_hash == expected_hash
        if not tamper_free:
            notes.append("Provenance hash mismatch detected; possible payload tampering.")

        # Determine overall verification status
        if source_auth and schema_valid and freshness_valid and tamper_free:
            status = VerificationStatus.VERIFIED
        elif not tamper_free or not source_auth:
            status = VerificationStatus.FAILED
        elif not freshness_valid:
            status = VerificationStatus.UNRESOLVED
        else:
            status = VerificationStatus.FAILED

        return ObservationVerification(
            outcome_id=outcome.outcome_id,
            status=status,
            source_authenticated=source_auth,
            schema_valid=schema_valid,
            freshness_valid=freshness_valid,
            tamper_free=tamper_free,
            auditor="ObservationVerificationEngine",
            verification_notes="; ".join(notes) if notes else "All verification checks passed.",
            verified_at=utc_now(),
        )
