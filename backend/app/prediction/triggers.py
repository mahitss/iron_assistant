"""Preemptive Action Triggers, Policy Gating, and Safe Preemption Rules (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.triggers")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TriggerType(str, Enum):
    """6 trigger condition mechanisms (Spec 52)."""

    TIME = "TIME"
    THRESHOLD = "THRESHOLD"
    EVENT = "EVENT"
    STATE_CHANGE = "STATE_CHANGE"
    PATTERN = "PATTERN"
    VERIFIED_CONDITION = "VERIFIED_CONDITION"


class ActionClass(str, Enum):
    """Preemptive action classification governing authorization gating (Spec 55, 56)."""

    SAFE_PREEMPTION = "SAFE_PREEMPTION"      # Diagnostics, cache warming, drafting plan, report
    SAFE_PREEMPTIVE = "SAFE_PREEMPTION"      # Alias
    PREEMPTIVE_WRITE = "PREEMPTIVE_WRITE"    # Configuration tweak, scaling
    DESTRUCTIVE = "DESTRUCTIVE"              # Rollback, deletion, termination (strictly gated)
    READ_ONLY = "SAFE_PREEMPTION"            # Alias
    DIAGNOSTIC = "SAFE_PREEMPTION"           # Alias


class TriggerStatus(str, Enum):
    """Trigger lifecycle status."""

    PENDING = "PENDING"
    FIRED = "FIRED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"
    ACTIVE = "ACTIVE"


class TriggerUnauthorizedError(Exception):
    """Raised when an automated action attempts to execute without required policy or verification (Spec 54)."""


@dataclass
class PredictionTrigger:
    """Automated trigger linking verified forecast conditions to preemption policies (Spec 50-56)."""

    condition: str = ""
    condition_expr: str = ""
    trigger_type: TriggerType = TriggerType.THRESHOLD
    action_class: ActionClass = ActionClass.SAFE_PREEMPTION
    action_name: str = ""
    scope: str = ""
    required_evidence: List[str] = field(default_factory=list)
    authorization_scope: Dict[str, Any] = field(default_factory=dict)
    authorized: bool = False
    status: TriggerStatus = TriggerStatus.PENDING
    trigger_id: str = field(default_factory=lambda: f"trig_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.condition_expr and self.condition:
            self.condition_expr = self.condition
        elif not self.condition and self.condition_expr:
            self.condition = self.condition_expr

    def can_execute_automatically(self, has_verified_evidence: bool, is_policy_approved: bool = False) -> bool:
        """Enforce Spec 53-56:
        - Safe preemption (diagnostics, plans) can run if evidence verified.
        - Destructive actions NEVER execute automatically on prediction alone!
        """
        if self.action_class == ActionClass.DESTRUCTIVE:
            logger.critical("DESTRUCTIVE ACTION BLOCKED on prediction trigger %s. Explicit approval required.", self.trigger_id)
            return False

        if not has_verified_evidence:
            logger.warning("Trigger %s execution blocked: required evidence unverified.", self.trigger_id)
            return False

        if self.action_class == ActionClass.PREEMPTIVE_WRITE and not is_policy_approved and not self.authorized:
            logger.warning("Trigger %s write blocked: policy approval missing.", self.trigger_id)
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "condition": self.condition,
            "condition_expr": self.condition_expr,
            "trigger_type": self.trigger_type.value if hasattr(self.trigger_type, "value") else str(self.trigger_type),
            "action_class": self.action_class.value if hasattr(self.action_class, "value") else str(self.action_class),
            "action_name": self.action_name,
            "scope": self.scope,
            "required_evidence": self.required_evidence,
            "authorization_scope": self.authorization_scope,
            "authorized": self.authorized,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "created_at": self.created_at.isoformat(),
        }


def evaluate_trigger(trigger: PredictionTrigger, observed_state: Dict[str, Any]) -> tuple[bool, str]:
    """Evaluate condition against observed state and check authorization safety gates (Spec 53-56)."""
    # Check destructive boundary
    if trigger.action_class == ActionClass.DESTRUCTIVE:
        if not trigger.authorized:
            trigger.status = TriggerStatus.BLOCKED
            return False, "Destructive action blocked without explicit administrative authorization (Spec 54)"

    # Simple expression check
    cond = trigger.condition or trigger.condition_expr
    for key, val in observed_state.items():
        if key in cond:
            # check comparison
            if ">" in cond:
                parts = cond.split(">")
                try:
                    thresh = float(parts[1].strip())
                    if float(val) > thresh:
                        trigger.status = TriggerStatus.FIRED
                        return True, f"Condition '{cond}' verified met with value {val}"
                except Exception:
                    pass
            elif "<" in cond:
                parts = cond.split("<")
                try:
                    thresh = float(parts[1].strip())
                    if float(val) < thresh:
                        trigger.status = TriggerStatus.FIRED
                        return True, f"Condition '{cond}' verified met with value {val}"
                except Exception:
                    pass

    # Default check if required evidence present
    if trigger.required_evidence and all(k in observed_state for k in trigger.required_evidence):
        trigger.status = TriggerStatus.FIRED
        return True, "Required evidence present in observed state"

    return False, "Condition not met or required evidence absent"
