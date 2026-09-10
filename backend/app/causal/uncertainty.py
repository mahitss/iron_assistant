"""Qualitative confidence calibration and uncertainty representation (Task 55, Prompts #30, #159, #160)."""

from __future__ import annotations


def to_qualitative_confidence(score: float, is_verified: bool = False) -> str:
    """Prompt #159, #160: Avoids uncalibrated exact numbers; maps to qualitative confidence levels."""
    if is_verified:
        return "VERIFIED"
    if score >= 0.85:
        return "HIGH"
    elif score >= 0.50:
        return "MEDIUM"
    elif score >= 0.20:
        return "LOW"
    return "UNKNOWN"


def format_uncertainty_statement(
    confidence_level: str,
    evidence_count: int,
    confounders: list[str] | None = None,
    alternatives_count: int = 0,
) -> str:
    """Produces honest, human-readable uncertainty summaries."""
    statements = []
    if confidence_level in ("LOW", "UNKNOWN"):
        statements.append("Confidence is limited due to sparse or unverified telemetry.")
    elif confidence_level == "MEDIUM":
        statements.append("Supported by available traces, but confounding factors remain possible.")
    elif confidence_level == "HIGH":
        statements.append("Strongly supported by multi-signal telemetry and causal mechanisms.")
    elif confidence_level == "VERIFIED":
        statements.append("Empirically verified through controlled intervention or strict verification.")

    if confounders:
        statements.append(f"Potential confounders detected: {', '.join(confounders)}.")
    if alternatives_count > 0:
        statements.append(f"{alternatives_count} competing alternative explanation(s) remain viable.")

    return " ".join(statements)
