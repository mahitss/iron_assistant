"""Deterministic post-recovery verification and stability window monitoring for Kairo Reliability (Task 88)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional

from app.reliability.models import (
    IncidentLifecycleState,
    IncidentRecord,
    RecoveryExecutionRecord,
    RecoveryStrategyType,
    VerificationResult,
    VerificationState,
    generate_id,
)

logger = logging.getLogger("kairo.reliability.verifier")


class RecoveryVerifier:
    """Performs deterministic non-LLM health checks and manages incident stability windows."""

    def __init__(
        self,
        default_stability_window_seconds: float = 15.0,
        native_client: Optional[Any] = None,
        stability_window_seconds: Optional[float] = None,
    ) -> None:
        self.default_stability_window_seconds = (
            stability_window_seconds if stability_window_seconds is not None else default_stability_window_seconds
        )
        self._native_client = native_client

    def _get_native_client(self) -> Any:
        if self._native_client is None:
            try:
                from app.native.service import native_service
                if native_service and hasattr(native_service, "client"):
                    self._native_client = native_service.client
            except Exception:
                pass
        return self._native_client

    async def verify_recovery(
        self,
        component: str,
        strategy: RecoveryStrategyType,
        action_result: Dict[str, Any],
    ) -> VerificationResult:
        """Executes targeted deterministic verification probes depending on component."""
        comp = component.lower()
        logger.info("Verifying recovery for component '%s' after '%s'", component, strategy.value)

        # 1. Native Runtime Verification
        if comp in ("native_runtime", "rust_runtime", "ipc", "protocol"):
            client = self._get_native_client()
            if client:
                try:
                    # Probe health via ping/health
                    from app.native.models import RuntimeRequest
                    probe_req = RuntimeRequest(operation="sys.ping", deadline_ms=3000)
                    resp = await client.request(probe_req)
                    if resp.status.value == "OK":
                        return VerificationResult(
                            component=component,
                            state=VerificationState.VERIFIED_RECOVERED,
                            probe_name="sys.ping",
                            passed=True,
                            details={
                                "session_id": client.session_id,
                                "probe_response": resp.result,
                                "roundtrip_verified": True,
                            },
                        )
                    else:
                        return VerificationResult(
                            component=component,
                            state=VerificationState.RECOVERY_FAILED,
                            probe_name="sys.ping",
                            passed=False,
                            details={"error": str(resp.error)},
                        )
                except Exception as exc:
                    return VerificationResult(
                        component=component,
                        state=VerificationState.RECOVERY_FAILED,
                        probe_name="sys.ping",
                        passed=False,
                        details={"exception": str(exc)},
                    )
            return VerificationResult(
                component=component,
                state=VerificationState.RECOVERED_UNVERIFIED,
                probe_name="simulated_probe",
                passed=True,
                details={"simulated": True},
            )

        # 2. General verification based on action_result status
        status = action_result.get("status", "UNKNOWN")
        if status in ("COMPLETED", "OK", "RESOLVED"):
            return VerificationResult(
                component=component,
                state=VerificationState.VERIFIED_RECOVERED,
                probe_name="action_telemetry_check",
                passed=True,
                details=action_result,
            )
        elif status in ("FAILED", "ERROR", "REJECTED"):
            return VerificationResult(
                component=component,
                state=VerificationState.RECOVERY_FAILED,
                probe_name="action_telemetry_check",
                passed=False,
                details=action_result,
            )
        else:
            return VerificationResult(
                component=component,
                state=VerificationState.RECOVERED_UNVERIFIED,
                probe_name="action_telemetry_check",
                passed=False,
                details=action_result,
            )

    def initiate_stability_window(
        self,
        incident: IncidentRecord,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Transitions incident to MONITORING state for a defined stability window."""
        dur = duration_seconds if duration_seconds is not None else self.default_stability_window_seconds
        incident.monitoring_until = datetime.fromtimestamp(
            time.time() + dur,
            tz=timezone.utc,
        )
        if incident.current_state != IncidentLifecycleState.MONITORING:
            incident.transition_to(IncidentLifecycleState.MONITORING)
        logger.info(
            "Incident %s entered stability MONITORING for %.1fs (until %s)",
            incident.incident_id,
            dur,
            incident.monitoring_until.isoformat(),
        )

    def evaluate_stability_window(self, incident: IncidentRecord) -> bool:
        """Checks whether the stability window has elapsed cleanly.

        Returns True if stability window completed and incident can be RESOLVED.
        """
        if incident.current_state != IncidentLifecycleState.MONITORING:
            return False
        if not incident.monitoring_until:
            return True

        now_utc = datetime.now(timezone.utc)
        if now_utc >= incident.monitoring_until:
            incident.transition_to(IncidentLifecycleState.RESOLVED)
            incident.resolved_at = now_utc
            incident.resolution_summary = "Recovered and verified stable across monitoring window"
            logger.info("Incident %s successfully RESOLVED after stability window", incident.incident_id)
            return True
        return False
