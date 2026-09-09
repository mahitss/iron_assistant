"""Change Significance Classification and Risk Evaluation (Task 46)."""

from __future__ import annotations

from enum import Enum
import logging
from typing import Any, Dict

logger = logging.getLogger("kairo.perception.significance")


class ChangeSignificance(str, Enum):
    """5-tier classification of environmental change consequence (Spec 82)."""

    TRIVIAL = "TRIVIAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignificanceClassifier:
    """Classifies significance using deterministic policy rules and environmental context (Spec 82-86)."""

    @classmethod
    def evaluate_significance(
        cls,
        change_type_str: str,
        subject: str,
        environment: str,
        before: Any,
        after: Any,
        is_security_sensitive: bool = False,
    ) -> ChangeSignificance:
        """Deterministic policy evaluation of change impact (Spec 83-86)."""
        env_upper = environment.upper()
        subj_lower = subject.lower()

        # 1. Critical: Security, Auth, Permission changes (Spec 84)
        if is_security_sensitive or "security" in subj_lower or "permission" in subj_lower or "auth" in subj_lower:
            return ChangeSignificance.CRITICAL

        # 2. Production changes receive elevated significance (Spec 85)
        if env_upper == "PRODUCTION":
            if change_type_str in ["HEALTH_CHANGE", "VERSION_CHANGE", "CONFIG_CHANGE", "DELETED"]:
                # If health degraded or unhealthy
                if isinstance(after, dict) and after.get("status") in ["UNHEALTHY", "DEGRADED"]:
                    return ChangeSignificance.CRITICAL
                return ChangeSignificance.HIGH
            return ChangeSignificance.MEDIUM

        # 3. Health changes in staging/dev
        if change_type_str == "HEALTH_CHANGE":
            if isinstance(after, dict) and after.get("status") in ["UNHEALTHY", "FAILED"]:
                return ChangeSignificance.HIGH
            return ChangeSignificance.MEDIUM

        # 4. Routine state changes
        if change_type_str in ["CODE_CHANGE", "VERSION_CHANGE"]:
            return ChangeSignificance.MEDIUM

        if change_type_str == "STATE_CHANGE":
            return ChangeSignificance.LOW

        return ChangeSignificance.TRIVIAL
