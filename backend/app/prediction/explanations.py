"""Prediction Explanations, Human Transparency, and Chain-of-Thought Protection (Task 47)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("kairo.prediction.explanations")


class PredictionExplainer:
    """Generates concise, human-understandable explanations of predictions without exposing private chain-of-thought (Spec 124-127)."""

    @classmethod
    def explain(
        cls,
        subject: str,
        predicted_event: str,
        signals_summary: str,
        timeframe: str,
        uncertainty: float,
        key_assumptions: List[str],
    ) -> str:
        """Enforce Spec 124, 125: Provide concise explanation: signals, timeframe, uncertainty."""
        uncertainty_label = (
            "low uncertainty" if uncertainty < 0.2 else
            "moderate uncertainty" if uncertainty < 0.5 else
            "high uncertainty"
        )

        assumptions_str = (
            f" Key assumptions: {'; '.join(key_assumptions[:2])}."
            if key_assumptions else ""
        )

        # Example format (Spec 125):
        # "Queue depth has increased for 45 minutes. Based on the recent trend, capacity may become constrained within 20–40 minutes..."
        conf_val = 1.0 - uncertainty
        return (
            f"{signals_summary} Based on verified telemetry patterns, {subject} may experience "
            f"'{predicted_event}' in the {timeframe} (Confidence: {conf_val:.2f}, {uncertainty_label}, uncertainty={uncertainty:.2f}).{assumptions_str}"
        )

    @classmethod
    def generate_explanation(cls, pred: Any) -> str:
        subj = getattr(pred, "subject", "unknown_subject")
        ev = getattr(pred, "event", "unknown_event")
        win = getattr(pred, "prediction_window", "near-term")
        win_str = win.value if hasattr(win, "value") else str(win)
        conf = getattr(pred, "confidence", 0.5)
        assump = getattr(pred, "assumptions", [])
        ev_refs = getattr(pred, "evidence_refs", [])
        signals = f"Observed signals: {', '.join(ev_refs)}." if ev_refs else "Verified telemetry monitored."
        return cls.explain(
            subject=subj,
            predicted_event=ev,
            signals_summary=signals,
            timeframe=win_str,
            uncertainty=round(1.0 - conf, 3),
            key_assumptions=assump,
        )

