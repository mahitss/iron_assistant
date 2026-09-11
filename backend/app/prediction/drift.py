"""Forecast Drift Detection and Change-Point Analysis (Task 74, Spec 21, 23, 64).

Detects:
- Input data distribution drift
- Feature distribution drift
- Residual and error drift
- Calibration degradation drift
- Change-point / regime shifts (mean shift, variance explosion)
- Classifies forecast health: HEALTHY, DEGRADED, DRIFTING, UNRELIABLE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.prediction.schemas import (
    DriftReport,
    ForecastHealthStatus,
)

logger = logging.getLogger("kairo.prediction.drift")


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float], mean_val: Optional[float] = None) -> float:
    if len(values) < 2:
        return 0.0
    m = mean_val if mean_val is not None else _mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


class ForecastDriftDetector:
    """Multi-axis statistical drift and regime change detector (Spec 21, 23)."""

    def __init__(
        self,
        target: str = "default_metric",
        z_threshold: float = 2.5,
        variance_ratio_threshold: float = 3.0,
        residual_multiplier_threshold: float = 2.5,
    ) -> None:
        self.target = target
        self.z_threshold = z_threshold
        self.variance_ratio_threshold = variance_ratio_threshold
        self.residual_multiplier_threshold = residual_multiplier_threshold
        self.drift_events: List[Dict[str, Any]] = []

    def record_drift_event(self, drift_type: str, score: float, description: str) -> None:
        self.drift_events.append({
            "drift_type": drift_type,
            "score": score,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_health_status(
        self,
        is_stale: bool = False,
        is_failed: bool = False,
        error_rate: Optional[float] = None,
    ) -> ForecastHealthStatus:
        if is_failed or (error_rate is not None and error_rate >= 0.40):
            return ForecastHealthStatus.UNRELIABLE
        if is_stale:
            return ForecastHealthStatus.STALE
        if any(e["drift_type"] == "CALIBRATION_DRIFT" for e in self.drift_events):
            return ForecastHealthStatus.DEGRADED
        if any(e["drift_type"] in ["INPUT_DATA_DRIFT", "REGIME_CHANGE"] for e in self.drift_events):
            return ForecastHealthStatus.DRIFTING
        return ForecastHealthStatus.HEALTHY

    def detect_regime_change(
        self,
        series: List[float],
        min_window: int = 5,
    ) -> Tuple[bool, str, float]:
        """Deterministic change-point detection on mean and variance shift (Spec 21).

        A change point indicates 'the generating process may have changed', NOT necessarily an incident.
        """
        if len(series) < min_window * 2:
            return False, "Insufficient observations for regime change analysis", 0.0

        n = len(series)
        split_point = n - min_window
        baseline = series[:split_point]
        recent = series[split_point:]

        m_base = _mean(baseline)
        s_base = _std(baseline, m_base)
        m_rec = _mean(recent)
        s_rec = _std(recent, m_rec)

        # 1. Sudden mean shift z-score
        effective_std = max(s_base, 0.01)
        z_shift = abs(m_rec - m_base) / (effective_std / math.sqrt(len(recent)))

        if z_shift >= self.z_threshold:
            desc = f"Regime mean shift detected: z-score={z_shift:.2f} (baseline={m_base:.2f} -> recent={m_rec:.2f})"
            return True, desc, z_shift

        # 2. Variance explosion
        if s_base > 1e-4:
            v_ratio = (s_rec ** 2) / (s_base ** 2)
            if v_ratio >= self.variance_ratio_threshold:
                desc = f"Regime volatility surge detected: variance ratio={v_ratio:.2f} (base_std={s_base:.2f} -> rec_std={s_rec:.2f})"
                return True, desc, v_ratio

        return False, "Process distribution stable across historical split", z_shift

    def detect_residual_drift(
        self,
        recent_errors: List[float],
        historical_errors: List[float],
    ) -> Tuple[bool, str, float]:
        """Detects if recent forecast errors deviate significantly from historical error profile (Spec 23)."""
        if not recent_errors or not historical_errors or len(historical_errors) < 5:
            return False, "Insufficient error history for residual drift check", 0.0

        hist_abs = [abs(e) for e in historical_errors]
        rec_abs = [abs(e) for e in recent_errors]

        m_hist = _mean(hist_abs)
        s_hist = _std(hist_abs, m_hist)
        m_rec = _mean(rec_abs)

        cutoff = m_hist + self.residual_multiplier_threshold * max(s_hist, 0.1)
        if m_rec > cutoff:
            drift_score = m_rec / max(m_hist, 0.01)
            desc = (
                f"Residual error drift: recent MAE ({m_rec:.4f}) exceeds "
                f"historical baseline ({m_hist:.4f} + {self.residual_multiplier_threshold}*std = {cutoff:.4f})"
            )
            return True, desc, drift_score

        return False, "Residual error within expected historical distribution", m_rec / max(m_hist, 0.01)

    def detect_calibration_drift(
        self,
        recent_brier: float,
        baseline_brier: float,
        threshold_pct: float = 40.0,
    ) -> Tuple[bool, str]:
        """Detects if probability calibration has degraded significantly (Spec 14, 23)."""
        if baseline_brier < 1e-6:
            return False, "Baseline calibration score too small to evaluate relative drift"

        pct_increase = ((recent_brier - baseline_brier) / baseline_brier) * 100.0
        if pct_increase >= threshold_pct:
            return True, f"Calibration degraded: Brier score deteriorated by {pct_increase:.1f}% ({baseline_brier:.3f} -> {recent_brier:.3f})"

        return False, f"Calibration stable: relative Brier delta is {pct_increase:.1f}%"

    def evaluate_target_drift(
        self,
        target: str,
        series: List[float],
        recent_errors: Optional[List[float]] = None,
        historical_errors: Optional[List[float]] = None,
        current_brier: Optional[float] = None,
        baseline_brier: Optional[float] = None,
    ) -> DriftReport:
        """Run comprehensive multi-axis drift analysis and output a structured DriftReport."""
        # 1. Check regime change on time-series values
        regime_hit, regime_desc, regime_score = self.detect_regime_change(series)
        if regime_hit:
            return DriftReport(
                target=target,
                drift_detected=True,
                drift_type="REGIME_CHANGE",
                p_value_or_score=round(regime_score, 4),
                threshold=self.z_threshold,
                description=regime_desc,
                recommended_action="Recalibrate forecast baseline and expand uncertainty intervals",
            )

        # 2. Check residual drift
        if recent_errors and historical_errors:
            res_hit, res_desc, res_score = self.detect_residual_drift(recent_errors, historical_errors)
            if res_hit:
                return DriftReport(
                    target=target,
                    drift_detected=True,
                    drift_type="RESIDUAL_DRIFT",
                    p_value_or_score=round(res_score, 4),
                    threshold=self.residual_multiplier_threshold,
                    description=res_desc,
                    recommended_action="Downgrade strategy trust and switch to conservative baseline",
                )

        # 3. Check calibration drift
        if current_brier is not None and baseline_brier is not None:
            cal_hit, cal_desc = self.detect_calibration_drift(current_brier, baseline_brier)
            if cal_hit:
                return DriftReport(
                    target=target,
                    drift_detected=True,
                    drift_type="CALIBRATION_DRIFT",
                    p_value_or_score=round(current_brier, 4),
                    threshold=baseline_brier,
                    description=cal_desc,
                    recommended_action="Trigger metacognitive calibration audit and damp confidence",
                )

        return DriftReport(
            target=target,
            drift_detected=False,
            drift_type="NONE",
            p_value_or_score=0.0,
            threshold=0.05,
            description="Process dynamics and model error distributions remain stable",
            recommended_action="Maintain standard forecast monitoring cadence",
        )

    def determine_health_status(
        self,
        drift_report: DriftReport,
        is_stale: bool = False,
        is_uncalibrated: bool = False,
        is_failed: bool = False,
    ) -> ForecastHealthStatus:
        """Determines explicit health classification from evidence (Spec 64)."""
        if is_failed:
            return ForecastHealthStatus.FAILED
        if is_stale:
            return ForecastHealthStatus.STALE
        if drift_report.drift_detected:
            if drift_report.drift_type == "REGIME_CHANGE":
                return ForecastHealthStatus.DRIFTING
            return ForecastHealthStatus.DEGRADED
        if is_uncalibrated:
            return ForecastHealthStatus.UNCERTAIN
        return ForecastHealthStatus.HEALTHY


forecast_drift_detector = ForecastDriftDetector()


def detect_input_data_drift(
    target: str,
    baseline_sample: List[float],
    current_sample: List[float],
) -> DriftReport:
    m_base = _mean(baseline_sample)
    s_base = _std(baseline_sample, m_base)
    m_curr = _mean(current_sample)
    diff = abs(m_curr - m_base)
    effective_std = max(s_base, 0.01)
    z = diff / (effective_std / math.sqrt(max(1, len(current_sample))))
    drift_hit = z >= 2.0 or diff > (s_base * 2.0)
    return DriftReport(
        target=target,
        drift_detected=drift_hit,
        drift_type="INPUT_DATA_DRIFT" if drift_hit else "NONE",
        p_value_or_score=round(z, 4),
        threshold=2.0,
        description=f"Input mean shift delta={diff:.4f}, z={z:.2f}",
        recommended_action="Update feature pipeline normalization" if drift_hit else "Maintain standard feature processing",
    )


def detect_residual_drift(
    target: str,
    historical_errors: List[float],
    recent_errors: List[float],
) -> DriftReport:
    detector = ForecastDriftDetector(target=target)
    hit, desc, score = detector.detect_residual_drift(recent_errors=recent_errors, historical_errors=historical_errors)
    return DriftReport(
        target=target,
        drift_detected=hit,
        drift_type="RESIDUAL_DRIFT" if hit else "NONE",
        p_value_or_score=round(score, 4),
        threshold=detector.residual_multiplier_threshold,
        description=desc if hit else "Residuals within expected bounds",
        recommended_action="Downgrade strategy trust" if hit else "Maintain strategy",
    )


def detect_calibration_drift(
    target: str,
    baseline_brier: float,
    current_brier: float,
) -> DriftReport:
    detector = ForecastDriftDetector(target=target)
    hit, desc = detector.detect_calibration_drift(recent_brier=current_brier, baseline_brier=baseline_brier)
    return DriftReport(
        target=target,
        drift_detected=hit,
        drift_type="CALIBRATION_DRIFT" if hit else "NONE",
        p_value_or_score=round(current_brier, 4),
        threshold=baseline_brier,
        description=desc,
        recommended_action="Recalibrate probabilities" if hit else "Calibration stable",
    )


def detect_regime_change(
    target: str,
    pre_window: List[float],
    post_window: List[float],
) -> DriftReport:
    series = list(pre_window) + list(post_window)
    detector = ForecastDriftDetector(target=target)
    hit, desc, score = detector.detect_regime_change(series, min_window=len(post_window))
    return DriftReport(
        target=target,
        drift_detected=hit,
        drift_type="REGIME_CHANGE" if hit else "NONE",
        p_value_or_score=round(score, 4),
        threshold=detector.z_threshold,
        description=desc,
        recommended_action="Expand prediction interval and refresh baseline" if hit else "Process stable",
    )

