"""Change Detection, Structural Diffing, and Burst Correlation (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.perception.observations import Observation
from app.perception.significance import ChangeSignificance, SignificanceClassifier

logger = logging.getLogger("kairo.perception.changes")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChangeType(str, Enum):
    """8 standardized environmental mutation classifications (Spec 80)."""

    STATE_CHANGE = "STATE_CHANGE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    CODE_CHANGE = "CODE_CHANGE"
    HEALTH_CHANGE = "HEALTH_CHANGE"
    VERSION_CHANGE = "VERSION_CHANGE"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    RESOURCE_CHANGE = "RESOURCE_CHANGE"
    BEHAVIOR_CHANGE = "BEHAVIOR_CHANGE"


@dataclass
class ChangeEvent:
    """Explicitly observed mutation between previous and current state (Spec 79-81)."""

    change_id: str
    subject: str
    change_type: ChangeType
    before: Any
    after: Any
    timestamp: datetime = field(default_factory=utc_now)
    source_id: str = ""
    significance: ChangeSignificance = ChangeSignificance.LOW
    evidence: Dict[str, Any] = field(default_factory=dict)
    environment: str = "DEVELOPMENT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "subject": self.subject,
            "change_type": self.change_type.value,
            "before": self.before,
            "after": self.after,
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "significance": self.significance.value,
            "evidence": self.evidence,
            "environment": self.environment,
        }


class ChangeDetector:
    """Tracks state deltas, groups change bursts, and evaluates change significance (Spec 79-88)."""

    def __init__(self, burst_window_seconds: float = 3.0) -> None:
        self.burst_window_seconds = burst_window_seconds
        # subject -> previous_state_value
        self._last_known_states: Dict[str, Any] = {}
        # burst buffer: subject_prefix -> list of recent changes
        self._burst_buffers: Dict[str, List[ChangeEvent]] = {}

    def detect_change(
        self,
        observation: Observation,
        environment: str = "DEVELOPMENT",
        is_security_sensitive: bool = False,
    ) -> Optional[ChangeEvent]:
        """Compare current observation with prior state and generate ChangeEvent if mutated (Spec 79-81)."""
        subj = observation.subject
        prev = self._last_known_states.get(subj)
        curr = observation.data

        # If unchanged, no delta
        if prev is not None and prev == curr:
            return None

        # Determine change type
        if "health" in subj or "status" in curr:
            ctype = ChangeType.HEALTH_CHANGE
        elif "git" in subj or "commit" in curr:
            ctype = ChangeType.CODE_CHANGE
        elif "version" in curr or "deployment" in subj:
            ctype = ChangeType.VERSION_CHANGE
        elif "config" in subj:
            ctype = ChangeType.CONFIG_CHANGE
        elif is_security_sensitive or "perm" in subj:
            ctype = ChangeType.PERMISSION_CHANGE
        else:
            ctype = ChangeType.STATE_CHANGE

        sig = SignificanceClassifier.evaluate_significance(
            change_type_str=ctype.value,
            subject=subj,
            environment=environment,
            before=prev,
            after=curr,
            is_security_sensitive=is_security_sensitive,
        )

        chg_id = f"chg_{uuid.uuid4().hex[:10]}"
        change = ChangeEvent(
            change_id=chg_id,
            subject=subj,
            change_type=ctype,
            before=prev,
            after=curr,
            timestamp=observation.observed_at,
            source_id=observation.source_id,
            significance=sig,
            evidence={
                "observation_id": observation.observation_id,
                "latency_ms": observation.latency_ms,
                "confidence": observation.confidence,
            },
            environment=environment,
        )

        # Update last known state
        self._last_known_states[subj] = curr
        logger.info("Detected %s on '%s' (sig=%s)", ctype.value, subj, sig.value)
        return change

    def aggregate_change_bursts(self, changes: List[ChangeEvent]) -> List[ChangeEvent]:
        """Enforce Spec 88: Correlate bursts (e.g. 100 file changes -> one logical change set)."""
        if len(changes) <= 1:
            return changes

        # Group by subject prefix or source
        groups: Dict[str, List[ChangeEvent]] = {}
        for c in changes:
            prefix = c.subject.split(":")[0] if ":" in c.subject else "general"
            groups.setdefault(prefix, []).append(c)

        result: List[ChangeEvent] = []
        for prefix, grp in groups.items():
            if len(grp) >= 5:
                # Synthesize aggregate change
                agg_id = f"burst_{uuid.uuid4().hex[:8]}"
                highest_sig = max((c.significance for c in grp), key=lambda s: ["TRIVIAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"].index(s.value))
                agg = ChangeEvent(
                    change_id=agg_id,
                    subject=f"{prefix}:burst_aggregate",
                    change_type=ChangeType.RESOURCE_CHANGE,
                    before=f"{len(grp)} prior items",
                    after=f"{len(grp)} modified items in burst",
                    timestamp=grp[-1].timestamp,
                    source_id=grp[0].source_id,
                    significance=highest_sig,
                    evidence={"burst_count": len(grp), "member_changes": [c.change_id for c in grp]},
                    environment=grp[0].environment,
                )
                result.append(agg)
            else:
                result.extend(grp)

        return result
