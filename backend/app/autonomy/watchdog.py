"""Autonomous Execution Watchdog and Anomaly Detection (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.autonomy.deadlines import DeadlineTracker
from app.autonomy.heartbeat import HeartbeatTracker
from app.autonomy.leases import ExecutionLeaseManager
from app.autonomy.state import AutonomousRunState

logger = logging.getLogger("kairo.autonomy.watchdog")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class WatchdogInspectionResult:
    """Diagnostic outcome and recommended recovery action for an anomalous run (Spec 26, 27)."""

    run_id: str
    issue_detected: str  # STUCK, EXPIRED, UNRESPONSIVE, ORPHANED, HEALTHY
    recommended_action: str  # RESUME, RETRY, REASSIGN, REPLAN, PAUSE, FAIL, NONE
    details: Dict[str, Any] = field(default_factory=dict)
    inspected_at: datetime = field(default_factory=utc_now)


class AutonomyWatchdog:
    """Supervises active runs, detects anomalies, and prescribes safe recovery (Spec 25-27)."""

    def __init__(
        self,
        lease_manager: ExecutionLeaseManager,
        heartbeat_tracker: HeartbeatTracker,
        stuck_step_threshold_seconds: int = 120,
    ) -> None:
        self.lease_manager = lease_manager
        self.heartbeat_tracker = heartbeat_tracker
        self.stuck_step_threshold = stuck_step_threshold_seconds

    def inspect_run(
        self,
        run_id: str,
        current_state: AutonomousRunState,
        step_started_at: Optional[datetime] = None,
        deadline: Optional[datetime] = None,
        has_active_agents: bool = False,
    ) -> WatchdogInspectionResult:
        """Inspect run health without immediately killing; determine surgical recovery (Spec 26)."""
        now = utc_now()

        # 1. Check deadline expiration (Spec 53)
        if deadline and now >= deadline:
            return WatchdogInspectionResult(
                run_id=run_id,
                issue_detected="EXPIRED",
                recommended_action="FAIL",
                details={"reason": f"Run deadline exceeded at {deadline.isoformat()}"},
            )

        # Non-running states don't require lease/heartbeat watchdog
        if current_state not in [AutonomousRunState.RUNNING, AutonomousRunState.RECOVERING, AutonomousRunState.REPLANNING]:
            return WatchdogInspectionResult(
                run_id=run_id,
                issue_detected="HEALTHY",
                recommended_action="NONE",
                details={"state": current_state.value},
            )

        # 2. Check lease and heartbeat responsiveness (Spec 25)
        lease = self.lease_manager.get_lease(run_id)
        is_alive = self.heartbeat_tracker.is_worker_alive(run_id)

        if not lease or lease.is_expired:
            return WatchdogInspectionResult(
                run_id=run_id,
                issue_detected="ORPHANED",
                recommended_action="REASSIGN",
                details={"reason": "Execution lease expired or missing; worker likely crashed."},
            )

        if not is_alive:
            return WatchdogInspectionResult(
                run_id=run_id,
                issue_detected="UNRESPONSIVE",
                recommended_action="RETRY",
                details={"reason": "Worker missed consecutive heartbeats."},
            )

        # 3. Check for stuck execution step (Spec 26)
        if step_started_at:
            elapsed = (now - step_started_at).total_seconds()
            if elapsed > self.stuck_step_threshold:
                # If agents are still actively calculating, allow replan instead of immediate termination
                action = "REPLAN" if has_active_agents else "PAUSE"
                return WatchdogInspectionResult(
                    run_id=run_id,
                    issue_detected="STUCK",
                    recommended_action=action,
                    details={
                        "reason": f"Step running for {elapsed:.1f}s exceeding threshold {self.stuck_step_threshold}s",
                        "has_active_agents": has_active_agents,
                    },
                )

        return WatchdogInspectionResult(
            run_id=run_id,
            issue_detected="HEALTHY",
            recommended_action="NONE",
            details={"state": current_state.value},
        )
