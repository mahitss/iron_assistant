"""Safety, security boundaries, and execution firewall for Situational Awareness (Task 60)."""

from __future__ import annotations

import re
from typing import Any


class SituationalAwarenessSafetyError(Exception):
    """Base exception for situational awareness safety violations."""


class SituationalAwarenessExecutionBoundaryError(SituationalAwarenessSafetyError):
    """Raised when situational awareness engine attempts direct side-effecting execution."""


# Regex patterns and replacements for credential and secret scrubbing
_SECRET_REPLACEMENTS = [
    (
        re.compile(
            r'(?i)(password|secret|api[_-]?key|token|auth[_-]?token|bearer|private[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?'
        ),
        r"\1: [REDACTED_SECRET]",
    ),
    (re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})"), r"\1[REDACTED_SECRET]"),
    (
        re.compile(r"(?i)-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----"),
        r"[REDACTED_SECRET]",
    ),
    (re.compile(r"(?i)AKIA[0-9A-Z]{16}"), r"[REDACTED_SECRET]"),
    (re.compile(r"(?i)(?:ghp|gho)_[a-zA-Z0-9]{36}"), r"[REDACTED_SECRET]"),
]

# Injection indicators in external event payloads
_INJECTION_INDICATORS = [
    "delete all databases",
    "drop table",
    "rm -rf",
    "ignore previous instructions",
    "bypass authorization",
    "grant root",
    "disable security",
    "override policy",
    "elevate privilege",
    "unrestricted production tool",
]


def scrub_situation_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_REPLACEMENTS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_situation_directive(directive: str) -> str:
    """Detect and neutralize prompt injection attempts in event text or situation descriptions.

    Raises:
        SituationalAwarenessSafetyError: If malicious injection attempt is detected.
    """
    if not directive:
        return directive
    lowered = directive.lower()
    for indicator in _INJECTION_INDICATORS:
        if indicator in lowered:
            raise SituationalAwarenessSafetyError(
                f"Malicious directive or prompt injection detected in event text: '{indicator}'"
            )
    return scrub_situation_secrets(directive.strip())


def block_direct_situation_action(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Situational awareness assesses and correlates, but NEVER directly executes tools.

    All execution must flow through:
    Situational Awareness -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    raise SituationalAwarenessExecutionBoundaryError(
        f"Execution Boundary Violation: Situational awareness engine cannot directly execute action '{action_name}'. "
        "Execution must be routed through Policy, Authorization, Approval, and ToolExecutor."
    )


def protect_baseline_from_incident(is_incident: bool, baseline_quarantined: bool) -> bool:
    """Invariant 21: Baselines must not be poisoned by incident observations.

    Returns True if observation can be incorporated, False if quarantined.
    """
    if is_incident or baseline_quarantined:
        return False
    return True


def verify_replay_safety(is_replay: bool, environment: str) -> bool:
    """Invariant 19 & 52: Historical replay must never trigger real-world side effects or production mutations."""
    if is_replay and environment.lower() == "production":
        raise SituationalAwarenessSafetyError(
            "Replay Safety Violation: Historical event replay is strictly prohibited in production environment."
        )
    return True


from dataclasses import dataclass
import time


@dataclass
class AdmissionDecision:
    admitted: bool
    reason: str
    backpressure_active: bool = False


class SituationStormProtector:
    """Bounded storm protection and backpressure manager for high-frequency signal bursts (Section 32)."""

    def __init__(
        self,
        max_active_situations: int = 100,
        max_signals_per_second: int = 500,
        storm_burst_threshold: int = 1000,
        cooldown_window_seconds: float = 60.0,
    ) -> None:
        self.max_active_situations = max_active_situations
        self.max_signals_per_second = max_signals_per_second
        self.storm_burst_threshold = storm_burst_threshold
        self.cooldown_window_seconds = cooldown_window_seconds
        self._signal_timestamps: list[float] = []
        self._storm_mode_active = False

    def is_storm_active(self) -> bool:
        return self._storm_mode_active

    def check_ingest_rate_limit(self, current_time: float) -> tuple[bool, str]:
        """Sliding window rate limit check. Returns (allowed, reason)."""
        # Trim timestamps older than 1 second
        one_sec_ago = current_time - 1.0
        self._signal_timestamps = [t for t in self._signal_timestamps if t >= one_sec_ago]

        if len(self._signal_timestamps) >= self.storm_burst_threshold:
            self._storm_mode_active = True
            return False, f"Signal storm detected ({len(self._signal_timestamps)} sig/s). Ingestion backpressure triggered."

        if len(self._signal_timestamps) >= self.max_signals_per_second:
            return False, f"Ingestion rate limit exceeded ({self.max_signals_per_second} sig/s)."

        self._signal_timestamps.append(current_time)
        self._storm_mode_active = False
        return True, "Rate limit nominal."

    def check_situation_capacity(self, current_active_count: int) -> tuple[bool, str]:
        """Guards against unbounded situation proliferation under noisy environments."""
        if current_active_count >= self.max_active_situations:
            return False, f"Maximum active situations capacity reached ({self.max_active_situations}). New situation formation queued/suppressed."
        return True, "Capacity available."

    def check_signal_admission(self, source_type: str, current_active_situations: int) -> AdmissionDecision:
        """Evaluate storm rate limit and situation capacity before admitting signal."""
        now_ts = time.time()
        allowed, reason = self.check_ingest_rate_limit(now_ts)
        if not allowed:
            return AdmissionDecision(admitted=False, reason=reason, backpressure_active=self.is_storm_active())
        cap_allowed, cap_reason = self.check_situation_capacity(current_active_situations)
        if not cap_allowed:
            return AdmissionDecision(admitted=False, reason=cap_reason, backpressure_active=True)
        return AdmissionDecision(admitted=True, reason="Admitted", backpressure_active=False)


# Global storm protector singleton
storm_protector = SituationStormProtector()

