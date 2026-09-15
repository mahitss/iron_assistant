"""Progressive canary rollout manager with automated threshold rollback (Task 91 Phase 9)."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

from app.capability_lifecycle.models import (
    CanaryRolloutConfig,
    CanaryRolloutState,
    CapabilityMetadata,
    LifecycleState,
    RolloutState,
    _now_utc,
    generate_cl_id,
)
from app.capability_lifecycle.state_machine import CapabilityStateMachine, get_capability_state_machine

logger = logging.getLogger("kairo.capability_lifecycle.canary")


class CanaryRolloutManager:
    """Orchestrates progressive canary deployments and trips automated rollbacks on anomaly detection."""

    def __init__(self, state_machine: Optional[CapabilityStateMachine] = None) -> None:
        self.state_machine = state_machine or get_capability_state_machine()
        # capability_id -> CanaryRolloutState
        self._active_rollouts: Dict[str, CanaryRolloutState] = {}

    def start_canary(
        self,
        capability: CapabilityMetadata,
        target_version: str,
        config: Optional[CanaryRolloutConfig] = None,
        actor: str = "rollout_controller",
    ) -> CanaryRolloutState:
        """Transitions capability to CANARY state and initializes progressive traffic routing."""
        cap_id = capability.capability_id
        cfg = config or CanaryRolloutConfig()

        rollout = CanaryRolloutState(
            rollout_id=generate_cl_id("roll"),
            capability_id=cap_id,
            target_version=target_version,
            config=cfg,
            current_percent=cfg.canary_percent,
            workloads_routed=0,
            errors_encountered=0,
            error_rate=0.0,
            state=RolloutState.CANARY_RUNNING,
            started_at=_now_utc(),
        )
        self._active_rollouts[cap_id] = rollout
        capability.canary_version_id = target_version

        # Transition capability to CANARY state
        self.state_machine.transition(
            capability,
            LifecycleState.CANARY,
            reason=f"Canary deployment initiated for v{target_version} ({cfg.canary_percent}% traffic)",
            actor=actor,
        )

        logger.info(
            "Started canary rollout for %s v%s at %.1f%% traffic",
            cap_id,
            target_version,
            cfg.canary_percent,
        )
        return rollout

    def record_canary_traffic(
        self,
        capability: CapabilityMetadata,
        is_error: bool = False,
        latency_ms: float = 20.0,
    ) -> Tuple[bool, Optional[str]]:
        """Ingests live workload telemetry; automatically aborts canary if SLA thresholds are breached."""
        cap_id = capability.capability_id
        rollout = self._active_rollouts.get(cap_id)
        if not rollout or rollout.state != RolloutState.CANARY_RUNNING:
            return True, None

        rollout.workloads_routed += 1
        if is_error:
            rollout.errors_encountered += 1

        rollout.error_rate = round(rollout.errors_encountered / max(1, rollout.workloads_routed), 4)

        # 1. Evaluate Error Rate SLA Breach
        if (
            rollout.workloads_routed >= 10
            and rollout.error_rate > rollout.config.error_rate_threshold
        ):
            abort_msg = (
                f"Canary error rate {rollout.error_rate * 100:.1f}% exceeded SLA threshold "
                f"{rollout.config.error_rate_threshold * 100:.1f}%"
            )
            self.abort_canary(capability, reason=abort_msg)
            return False, abort_msg

        # 2. Evaluate Latency Spike Breach
        if latency_ms > rollout.config.latency_threshold_ms:
            abort_msg = f"Canary latency {latency_ms:.1f}ms breached threshold {rollout.config.latency_threshold_ms:.1f}ms"
            self.abort_canary(capability, reason=abort_msg)
            return False, abort_msg

        return True, None

    def abort_canary(
        self,
        capability: CapabilityMetadata,
        reason: str,
        actor: str = "automated_rollback_safeguard",
    ) -> CanaryRolloutState:
        """Immediately halts canary rollout fail-closed and transitions capability to DEGRADED."""
        cap_id = capability.capability_id
        rollout = self._active_rollouts.get(cap_id)
        if rollout:
            rollout.state = RolloutState.ABORTED
            rollout.completed_at = _now_utc()
            rollout.abort_reason = reason

        capability.canary_version_id = None

        # Transition capability to DEGRADED state
        self.state_machine.transition(
            capability,
            LifecycleState.DEGRADED,
            reason=f"Canary rollout aborted: {reason}",
            actor=actor,
        )

        logger.warning("Aborted canary rollout for %s: %s", cap_id, reason)
        return rollout or CanaryRolloutState(capability_id=cap_id, target_version=capability.version)

    def complete_canary(
        self,
        capability: CapabilityMetadata,
        actor: str = "rollout_controller",
    ) -> CanaryRolloutState:
        """Marks canary stage as successfully completed, ready for final active promotion."""
        cap_id = capability.capability_id
        rollout = self._active_rollouts.get(cap_id)
        if rollout:
            rollout.state = RolloutState.PROMOTED
            rollout.completed_at = _now_utc()

        logger.info("Canary completed successfully for %s v%s", cap_id, capability.version)
        return rollout or CanaryRolloutState(capability_id=cap_id, target_version=capability.version)

    def get_active_rollout(self, capability_id: str) -> Optional[CanaryRolloutState]:
        return self._active_rollouts.get(capability_id)


_global_canary_manager: Optional[CanaryRolloutManager] = None


def get_canary_rollout_manager() -> CanaryRolloutManager:
    global _global_canary_manager
    if _global_canary_manager is None:
        _global_canary_manager = CanaryRolloutManager()
    return _global_canary_manager
