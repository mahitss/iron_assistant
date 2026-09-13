"""Authority Escalation & Policy Bypass Detection Engine (Task 78).

Detects attempts to bypass policy, escalate privilege, weaken controls, or avoid approvals.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.policy.governance_schemas import (
    AuthorityEscalationReport,
    AuthorityLevel,
    GovernanceReviewRequest,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuthorityEscalationDetector:
    """Monitors, detects, and flags suspicious privilege escalation and security control tampering."""

    # Patterns indicating attempts to weaken controls or bypass governance
    CONTROL_WEAKENING_PATTERNS = [
        r"disable_.*security",
        r"bypass_.*approval",
        r"override_.*stop",
        r"kill_.*audit",
        r"drop_.*constitution",
        r"self_approve",
        r"grant_.*admin",
        r"elevate_.*role",
        r"weaken_.*policy",
        r"suppress_.*alert",
    ]

    def __init__(self, probe_threshold: int = 3, window_seconds: int = 60) -> None:
        self.probe_threshold = probe_threshold
        self.window_seconds = window_seconds
        # Caller -> list of (timestamp, request, denied)
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._incidents: list[AuthorityEscalationReport] = []

    def record_attempt(
        self,
        caller_id: str,
        request: GovernanceReviewRequest,
        denied: bool,
    ) -> None:
        """Record an evaluated request for historical velocity and probe analysis."""
        now = _now_utc()
        self._history[caller_id].append({
            "timestamp": now,
            "action": request.action,
            "resource": request.resource,
            "risk_level": request.risk_level,
            "denied": denied,
        })
        # Prune older than window
        cutoff = now - timedelta(seconds=self.window_seconds * 2)
        self._history[caller_id] = [
            h for h in self._history[caller_id] if h["timestamp"] >= cutoff
        ]

    def detect_escalation(
        self,
        request: GovernanceReviewRequest,
        current_authority: AuthorityLevel,
    ) -> AuthorityEscalationReport:
        """Analyze a requested action and caller context for privilege escalation and bypass signatures."""
        action_lower = request.action.lower()
        now = _now_utc()
        flagged_actions = []
        severity = "LOW"
        bypass_technique: str | None = None
        rationale_parts: list[str] = []

        # 1. Control Weakening / Governance Tampering Detection
        for pattern in self.CONTROL_WEAKENING_PATTERNS:
            if re.search(pattern, action_lower):
                bypass_technique = "CONTROL_WEAKENING"
                severity = "CRITICAL"
                flagged_actions.append(request.action)
                rationale_parts.append(
                    f"Action '{request.action}' matches control-weakening pattern '{pattern}'."
                )
                break

        # 2. Self-Approval or Emergency Stop Bypass Detection
        if "approval" in action_lower and ("approve" in action_lower or "self" in action_lower):
            if current_authority.rank < AuthorityLevel.ADMIN.rank:
                bypass_technique = "APPROVAL_BYPASS_ATTEMPT"
                severity = "HIGH"
                flagged_actions.append(request.action)
                rationale_parts.append("Unauthorized attempt to manipulate or self-approve governance reviews.")

        if "stop" in action_lower and ("resume" in action_lower or "cancel" in action_lower or "override" in action_lower):
            if current_authority.rank < AuthorityLevel.SYSTEM.rank:
                bypass_technique = "EMERGENCY_STOP_BYPASS"
                severity = "CRITICAL"
                flagged_actions.append(request.action)
                rationale_parts.append("Attempted tampering with emergency stop without SYSTEM/ADMIN authority.")

        # 3. Excessive Privilege Request / Privilege Creep Detection
        destructive_verbs = ["delete", "drop", "terminate", "destroy", "format", "purge"]
        is_destructive_action = any(v in action_lower for v in destructive_verbs) or request.is_destructive
        if is_destructive_action and current_authority.rank <= AuthorityLevel.LIMITED.rank:
            bypass_technique = bypass_technique or "PRIVILEGE_CREEP"
            if severity == "LOW":
                severity = "HIGH"
            flagged_actions.append(request.action)
            rationale_parts.append(
                f"Destructive action '{request.action}' attempted with insufficient authority level {current_authority.value}."
            )

        # 4. Probe Hammering / Rapid Denial Repetition Detection
        caller_history = self._history.get(request.caller_id, [])
        cutoff = now - timedelta(seconds=self.window_seconds)
        recent_denials = [
            h for h in caller_history if h["denied"] and h["timestamp"] >= cutoff
        ]
        if len(recent_denials) >= self.probe_threshold:
            bypass_technique = "PROBE_HAMMERING"
            severity = "HIGH" if severity != "CRITICAL" else "CRITICAL"
            flagged_actions.append(request.action)
            rationale_parts.append(
                f"Caller '{request.caller_id}' experienced {len(recent_denials)} denials within {self.window_seconds}s "
                f"(exceeds probe threshold {self.probe_threshold})."
            )

        is_escalation = bypass_technique is not None

        report = AuthorityEscalationReport(
            is_escalation_attempt=is_escalation,
            bypass_technique=bypass_technique,
            severity=severity,
            rationale="; ".join(rationale_parts) if rationale_parts else "No escalation signatures detected.",
            flagged_actions=flagged_actions,
        )

        if is_escalation:
            logger.warning(
                "Authority escalation flagged: caller=%s, technique=%s, severity=%s",
                request.caller_id,
                bypass_technique,
                severity,
            )
            self._incidents.append(report)

        return report

    def get_recent_incidents(self, limit: int = 50) -> list[AuthorityEscalationReport]:
        """Return recently recorded escalation incident reports."""
        return list(reversed(self._incidents[-limit:]))

    def reset_history(self) -> None:
        """Clear historical tracking cache (for testing or maintenance)."""
        self._history.clear()
        self._incidents.clear()


default_escalation_detector = AuthorityEscalationDetector()
