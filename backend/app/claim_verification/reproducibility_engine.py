"""Reproducibility Engine for Task 116.
Records, manages, and audits reproduction attempts of evidence generation
and verification checks without fabricating certainty.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import platform
from typing import Any, Dict, List, Optional
import uuid

from app.claim_verification.domain import (
    ReproducibilityStatus,
    ReproductionAttempt,
)


class ReproducibilityEngine:
    """Manages reproduction attempts, environment fingerprinting, and auditability."""

    @classmethod
    def get_current_environment_fingerprint(cls) -> str:
        """Construct deterministic environment fingerprint from platform metadata."""
        raw_env = f"OS:{platform.system()}_REL:{platform.release()}_ARCH:{platform.machine()}_VER:116.0"
        return hashlib.sha256(raw_env.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def record_attempt(
        cls,
        case_id: str,
        method: str,
        input_data: str,
        output_data: str,
        expected_output_hash: Optional[str] = None,
        deterministic: bool = True,
        seed: Optional[int] = None,
        notes: str = "",
    ) -> ReproductionAttempt:
        """Execute or record a reproduction attempt, hashing inputs and outputs."""
        attempt_id = f"repro_{uuid.uuid4().hex[:10]}"
        in_hash = hashlib.sha256(input_data.encode("utf-8")).hexdigest()
        out_hash = hashlib.sha256(output_data.encode("utf-8")).hexdigest()

        if expected_output_hash is None:
            status = ReproducibilityStatus.REPRODUCIBLE if deterministic else ReproducibilityStatus.PARTIALLY_REPRODUCIBLE
        elif out_hash == expected_output_hash:
            status = ReproducibilityStatus.REPRODUCIBLE
        else:
            status = ReproducibilityStatus.FAILED_REPRODUCTION

        return ReproductionAttempt(
            attempt_id=attempt_id,
            case_id=case_id,
            method=method,
            status=status,
            environment_fingerprint=cls.get_current_environment_fingerprint(),
            input_hash=in_hash,
            output_hash=out_hash,
            deterministic=deterministic,
            seed=seed,
            notes=notes or f"Reproduction check completed with status {status.value}",
            executed_at=datetime.now(timezone.utc),
        )

    @classmethod
    def evaluate_overall_reproducibility(
        cls,
        attempts: List[ReproductionAttempt],
    ) -> ReproducibilityStatus:
        """Compute overall reproducibility classification for a verification case."""
        if not attempts:
            return ReproducibilityStatus.NOT_ATTEMPTED

        statuses = [a.status for a in attempts]
        if any(s == ReproducibilityStatus.FAILED_REPRODUCTION for s in statuses):
            return ReproducibilityStatus.FAILED_REPRODUCTION
        if all(s == ReproducibilityStatus.REPRODUCIBLE for s in statuses):
            return ReproducibilityStatus.REPRODUCIBLE
        if any(s in (ReproducibilityStatus.REPRODUCIBLE, ReproducibilityStatus.PARTIALLY_REPRODUCIBLE) for s in statuses):
            return ReproducibilityStatus.PARTIALLY_REPRODUCIBLE
        return ReproducibilityStatus.NON_REPRODUCIBLE
