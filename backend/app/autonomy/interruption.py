"""Interruption Handling, Safe Pauses, and Emergency Stop Propagation (Task 45)."""

from __future__ import annotations

from enum import Enum
import logging
from typing import Callable, List, Optional

from app.autonomy.state import AutonomousRunState

logger = logging.getLogger("kairo.autonomy.interruption")


class InterruptionType(str, Enum):
    PAUSE = "PAUSE"
    CANCEL = "CANCEL"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class InterruptionHandler:
    """Coordinates user pauses, cancellations, and emergency stop cascades (Spec 65-71, 111-113)."""

    def __init__(self) -> None:
        self._pause_requested: bool = False
        self._cancel_requested: bool = False
        self._emergency_stop_triggered: bool = False
        self._stop_reason: Optional[str] = None
        self._child_cancellation_hooks: List[Callable[[], None]] = []

    def request_pause(self) -> None:
        """User requests safe pause before next consequential step (Spec 65-67)."""
        self._pause_requested = True
        logger.info("User requested execution pause; will pause before starting next consequential operation.")

    def request_cancel(self, reason: str = "User cancelled execution") -> None:
        """User cancels future work while preserving completed work and evidence (Spec 69, 70)."""
        self._cancel_requested = True
        self._stop_reason = reason
        self._propagate_cancellation()
        logger.info("Execution cancelled: %s", reason)

    def trigger_emergency_stop(self, reason: str = "Emergency stop invoked") -> None:
        """Immediate hard stop propagating to all agents, tools, and queued actions (Spec 68, 111, 112)."""
        self._emergency_stop_triggered = True
        self._stop_reason = reason
        self._propagate_cancellation()
        logger.critical("EMERGENCY STOP executed on autonomous run: %s", reason)

    def register_child_hook(self, hook: Callable[[], None]) -> None:
        """Register subagent or child task cancellation hook (Spec 112)."""
        self._child_cancellation_hooks.append(hook)

    def _propagate_cancellation(self) -> None:
        """Propagate halt cascade to all child agents and tasks."""
        for hook in self._child_cancellation_hooks:
            try:
                hook()
            except Exception as exc:
                logger.warning("Error propagating cancellation to child task: %s", exc)

    def clear_pause(self) -> None:
        """Clear pause state upon user resumption."""
        self._pause_requested = False

    @property
    def should_halt_immediately(self) -> bool:
        return self._emergency_stop_triggered or self._cancel_requested

    @property
    def should_pause(self) -> bool:
        return self._pause_requested

    @property
    def stop_reason(self) -> Optional[str]:
        return self._stop_reason
