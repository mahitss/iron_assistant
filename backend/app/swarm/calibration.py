"""Confidence calibration, correlated failure dampening, and overconfidence defense (Task 64)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConfidenceCalibrator:
    """Calibrates collective confidence based on empirical evidence and source independence (Spec 28, 29, 50)."""

    def calibrate_confidence(
        self,
        raw_confidence: float,
        evidence_count: int,
        independent_lineage_count: int,
        has_disagreements: bool,
        verification_passed: bool = False,
    ) -> float:
        """Calibrate collective confidence.

        Invariants:
        - AGENT CONFIDENCE != CERTAINTY.
        - 5 agents agreeing != 5 independent confirmations.
        - If evidence is weak or unverified, confidence must remain limited.
        """
        calibrated = raw_confidence

        # 1. Dampen if evidence is sparse
        if evidence_count == 0:
            calibrated = min(calibrated, 0.50)
        elif evidence_count == 1:
            calibrated = min(calibrated, 0.70)

        # 2. Correlated failure defense: if multiple agents share only 1 root lineage, cap confidence
        if independent_lineage_count <= 1 and raw_confidence > 0.80:
            calibrated = min(calibrated, 0.78)

        # 3. Penalize active disagreements
        if has_disagreements:
            calibrated = max(0.40, calibrated - 0.15)

        # 4. Verification boost or cap
        if not verification_passed:
            # Cannot exceed 0.85 without independent verification
            calibrated = min(calibrated, 0.85)
        else:
            calibrated = min(0.98, calibrated + 0.08)

        final_conf = round(max(0.10, min(0.99, calibrated)), 2)
        logger.debug(
            "CONFIDENCE_CALIBRATED: raw=%.2f calibrated=%.2f ev_cnt=%d lineages=%d verified=%s",
            raw_confidence,
            final_conf,
            evidence_count,
            independent_lineage_count,
            verification_passed,
        )
        return final_conf
