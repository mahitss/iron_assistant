"""Post-incident learning, metacognitive calibration, and foresight integration (Task 88)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.reliability.models import (
    IncidentRecord,
    RecoveryExecutionRecord,
    VerificationState,
    generate_id,
)

logger = logging.getLogger("kairo.reliability.learning")


class ReliabilityCalibrationRecord(BaseModel):
    """Factual comparison between predicted recovery expectations and actual observed outcomes."""

    calibration_id: str = Field(default_factory=lambda: generate_id("cal"))
    incident_id: str
    component: str
    strategy: str
    predicted_duration_seconds: float = 30.0
    actual_duration_seconds: float
    predicted_cost: Dict[str, float] = Field(default_factory=dict)
    actual_cost: Dict[str, float] = Field(default_factory=dict)
    predicted_success_prob: float = 0.8
    actual_success: bool
    verification_confidence: float
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReliabilityLearner:
    """Computes calibration signals, updates empirical success rates, and pushes foresight warnings."""

    def __init__(self) -> None:
        # In-memory history: (component, strategy) -> List[ReliabilityCalibrationRecord]
        self._calibrations: Dict[str, List[ReliabilityCalibrationRecord]] = {}
        # Component empirical success rates: (component, strategy) -> float
        self._empirical_success_rates: Dict[str, float] = {}

    def record_outcome(
        self,
        incident: IncidentRecord,
        execution: RecoveryExecutionRecord,
        actual_duration_seconds: float,
        actual_cost: Optional[Dict[str, float]] = None,
    ) -> ReliabilityCalibrationRecord:
        """Records an execution outcome and calculates calibration error metrics."""
        success = execution.verification_state == VerificationState.VERIFIED_RECOVERED
        comp_key = f"{execution.component}:{execution.strategy.value}"

        record = ReliabilityCalibrationRecord(
            incident_id=incident.incident_id,
            component=execution.component,
            strategy=execution.strategy.value,
            predicted_duration_seconds=30.0,
            actual_duration_seconds=actual_duration_seconds,
            actual_cost=actual_cost or {},
            actual_success=success,
            verification_confidence=1.0 if success else 0.0,
        )

        history = self._calibrations.setdefault(comp_key, [])
        history.append(record)

        # Update empirical rolling success rate
        recent = history[-20:]  # Rolling 20 attempts
        self._empirical_success_rates[comp_key] = sum(1.0 for r in recent if r.actual_success) / len(recent)

        logger.info(
            "Reliability learning recorded for %s: success=%s, duration=%.2fs, empirical_rate=%.2f",
            comp_key,
            success,
            actual_duration_seconds,
            self._empirical_success_rates[comp_key],
        )

        # Foresight integration: publish early warning if failure rate is rising
        if self._empirical_success_rates[comp_key] < 0.5 and len(recent) >= 3:
            self._publish_foresight_warning(execution.component, self._empirical_success_rates[comp_key])

        return record

    def get_empirical_success_rate(self, component: str, strategy: str) -> float:
        """Returns empirical success rate for component and strategy (defaults to 0.85)."""
        key = f"{component}:{strategy}"
        return self._empirical_success_rates.get(key, 0.85)

    def _publish_foresight_warning(self, component: str, success_rate: float) -> None:
        """Publishes an early warning to Task 74 Foresight engine."""
        logger.warning(
            "FORESIGHT SIGNAL: Component '%s' recovery success rate degraded to %.1f%%; publishing early warning",
            component,
            success_rate * 100.0,
        )
        try:
            from app.events.bus import event_bus
            from app.events.schemas import Event, EventSeverity, ExecutionDomain
            # Emit standard foresight warning
            ev = Event(
                event_type="foresight.early_warning.emitted",
                severity=EventSeverity.WARNING,
                execution_domain=ExecutionDomain.SYSTEM,
                payload={
                    "source_component": component,
                    "warning_type": "HIGH_RECOVERY_FAILURE_RATE",
                    "recovery_success_rate": success_rate,
                    "recommended_action": "DEGRADE_CAPABILITY_PREEMPTIVELY",
                },
            )
            # Dispatch event non-blockingly
            import asyncio
            asyncio.create_task(event_bus.publish(ev))
        except Exception as exc:
            logger.debug("Foresight event publishing notice: %s", exc)
