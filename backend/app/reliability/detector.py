"""Failure detection, deduplication, storm detection, and crash loop analysis for Kairo Reliability (Task 88)."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.reliability.models import FailureRecord, IncidentLifecycleState, IncidentRecord
from app.reliability.taxonomy import FailureClassifier, FailureSeverity, FailureType

logger = logging.getLogger("kairo.reliability.detector")


class FailureDetector:
    """Consumes telemetry, exception, and event signals; deduplicates failures and detects storms/crash loops."""

    def __init__(
        self,
        dedup_window_seconds: float = 60.0,
        storm_threshold: int = 5,
        storm_window_seconds: float = 10.0,
        crash_loop_threshold: int = 3,
        crash_loop_window_seconds: float = 60.0,
    ) -> None:
        self.dedup_window_seconds = dedup_window_seconds
        self.storm_threshold = storm_threshold
        self.storm_window_seconds = storm_window_seconds
        self.crash_loop_threshold = crash_loop_threshold
        self.crash_loop_window_seconds = crash_loop_window_seconds

        # Sliding window timestamps: failure_fingerprint -> List[float (time.time())]
        self._failure_windows: Dict[str, List[float]] = {}
        # Component restart timestamps: component -> List[float]
        self._restart_history: Dict[str, List[float]] = {}
        # Crash history: component -> List[float]
        self._crash_history: Dict[str, List[float]] = {}
        # Components flagged in crash loop: component -> bool
        self._crash_loops: Set[str] = set()

    @staticmethod
    def compute_fingerprint(
        component: str,
        failure_type: FailureType,
        operation: str,
        message: str,
    ) -> str:
        """Compute a deterministic hash for deduplication and grouping."""
        norm_comp = component.strip().lower()
        norm_type = failure_type.value
        norm_op = operation.strip().lower()
        # Strip numbers and UUIDs from message to stabilize fingerprint
        norm_msg = "".join(c for c in message.lower() if c.isalpha())[:128]

        raw = f"{norm_comp}|{norm_type}|{norm_op}|{norm_msg}"
        return f"fp_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

    def ingest_signal(
        self,
        exc_or_error: Exception | str | dict[str, Any],
        component: str,
        operation: str = "unspecified",
        correlation_id: str | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        status_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FailureRecord:
        """Classifies, fingerprints, and creates a sanitized FailureRecord."""
        data = FailureClassifier.classify(
            exc_or_error=exc_or_error,
            component=component,
            operation=operation,
            correlation_id=correlation_id,
            trace_id=trace_id,
            causation_id=causation_id,
            status_code=status_code,
            metadata=metadata,
        )
        fp = self.compute_fingerprint(
            component=component,
            failure_type=data["failure_type"],
            operation=operation,
            message=data["message"],
        )
        data["fingerprint"] = fp

        record = FailureRecord(**data)

        # Track occurrence in sliding window
        now_ts = time.time()
        self._failure_windows.setdefault(fp, []).append(now_ts)

        # If it's a process/runtime failure, record in crash history
        if record.failure_type in (FailureType.PROCESS_FAILURE, FailureType.RUNTIME_FAILURE):
            self.record_crash(component)

        return record

    def record_restart(self, component: str) -> None:
        """Record component restart attempt for crash-loop tracking."""
        now_ts = time.time()
        cutoff = now_ts - self.crash_loop_window_seconds
        restarts = [t for t in self._restart_history.get(component, []) if t > cutoff]
        restarts.append(now_ts)
        self._restart_history[component] = restarts
        if len(restarts) >= self.crash_loop_threshold:
            self._crash_loops.add(component.lower())

    def record_crash(self, component: str) -> None:
        """Record component crash for crash-loop tracking."""
        now_ts = time.time()
        cutoff = now_ts - self.crash_loop_window_seconds
        crashes = [t for t in self._crash_history.get(component, []) if t > cutoff]
        crashes.append(now_ts)
        self._crash_history[component] = crashes

        # Check if crash loop threshold breached
        if len(crashes) >= self.crash_loop_threshold:
            restarts = [t for t in self._restart_history.get(component, []) if t > cutoff]
            if len(restarts) >= 1:
                self._crash_loops.add(component.lower())
                logger.critical(
                    "CRASH_LOOP_DETECTED for component '%s': %d crashes and %d restarts within %ds",
                    component,
                    len(crashes),
                    len(restarts),
                    self.crash_loop_window_seconds,
                )

    def is_in_crash_loop(self, component: str) -> bool:
        """Check if component is currently in an uncontained crash loop."""
        return component.lower() in self._crash_loops

    def clear_crash_loop(self, component: str) -> None:
        """Manually or post-verification clear crash loop status."""
        self._crash_loops.discard(component.lower())
        self._crash_history.pop(component, None)
        self._restart_history.pop(component, None)

    def detect_storm(self, fingerprint: str) -> bool:
        """Detect if identical failure is occurring in a high-frequency storm."""
        now_ts = time.time()
        cutoff = now_ts - self.storm_window_seconds
        history = [t for t in self._failure_windows.get(fingerprint, []) if t > cutoff]
        self._failure_windows[fingerprint] = history
        return len(history) >= self.storm_threshold

    def is_duplicate_in_window(self, fingerprint: str) -> bool:
        """Check if identical failure has occurred within the deduplication window."""
        now_ts = time.time()
        cutoff = now_ts - self.dedup_window_seconds
        history = [t for t in self._failure_windows.get(fingerprint, []) if t > cutoff]
        # Duplicate if more than 1 occurrence in window
        return len(history) > 1
