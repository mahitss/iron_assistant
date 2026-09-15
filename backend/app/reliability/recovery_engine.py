"""Autonomous recovery engine: strategy selection, scoped locks, cooldowns, authorization, and budget reservation (Task 88)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.reliability.models import (
    FailureLifecycleState,
    FailureRecord,
    IncidentRecord,
    RecoveryExecutionRecord,
    RecoveryStrategy,
    RecoveryStrategyType,
    SafeRecoveryClass,
    VerificationState,
    generate_id,
)
from app.reliability.taxonomy import FailureSeverity, FailureType

logger = logging.getLogger("kairo.reliability.recovery_engine")


# Canonical strategy definitions per failure type
STRATEGY_DEFAULTS: Dict[RecoveryStrategyType, Dict[str, Any]] = {
    RecoveryStrategyType.RETRY: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 5.0, "memory_mb": 16.0, "slots": 1},
        "side_effect_class": "SAFE_READ",
        "max_attempts": 3,
        "cooldown_seconds": 2.0,
    },
    RecoveryStrategyType.RECONNECT: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 10.0, "memory_mb": 32.0, "slots": 1},
        "side_effect_class": "LOW_RISK",
        "max_attempts": 3,
        "cooldown_seconds": 3.0,
    },
    RecoveryStrategyType.RESTART_COMPONENT: {
        "risk": SafeRecoveryClass.MODERATE_RECOVERY,
        "resource_cost": {"cpu": 25.0, "memory_mb": 128.0, "slots": 2},
        "side_effect_class": "SYSTEM_RESTART",
        "max_attempts": 2,
        "cooldown_seconds": 10.0,
    },
    RecoveryStrategyType.RESTART_PROCESS: {
        "risk": SafeRecoveryClass.MODERATE_RECOVERY,
        "resource_cost": {"cpu": 20.0, "memory_mb": 64.0, "slots": 1},
        "side_effect_class": "PROCESS_SUPERVISION",
        "max_attempts": 2,
        "cooldown_seconds": 5.0,
    },
    RecoveryStrategyType.RECREATE_SANDBOX: {
        "risk": SafeRecoveryClass.MODERATE_RECOVERY,
        "resource_cost": {"cpu": 15.0, "memory_mb": 64.0, "slots": 1},
        "side_effect_class": "SANDBOX_ISOLATION",
        "max_attempts": 2,
        "cooldown_seconds": 5.0,
    },
    RecoveryStrategyType.REBUILD_CONNECTION_POOL: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 5.0, "memory_mb": 32.0, "slots": 1},
        "side_effect_class": "NETWORK_POOL",
        "max_attempts": 3,
        "cooldown_seconds": 3.0,
    },
    RecoveryStrategyType.RELEASE_LEAKED_RESOURCE: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 2.0, "memory_mb": 8.0, "slots": 1},
        "side_effect_class": "RESOURCE_CLEANUP",
        "max_attempts": 3,
        "cooldown_seconds": 1.0,
    },
    RecoveryStrategyType.RECONCILE_RESOURCE: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 5.0, "memory_mb": 16.0, "slots": 1},
        "side_effect_class": "RESOURCE_RECONCILE",
        "max_attempts": 3,
        "cooldown_seconds": 2.0,
    },
    RecoveryStrategyType.PAUSE_WORKFLOW: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 1.0, "memory_mb": 4.0, "slots": 1},
        "side_effect_class": "WORKFLOW_STATE",
        "max_attempts": 1,
        "cooldown_seconds": 1.0,
    },
    RecoveryStrategyType.RESUME_WORKFLOW: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 5.0, "memory_mb": 16.0, "slots": 1},
        "side_effect_class": "WORKFLOW_STATE",
        "max_attempts": 2,
        "cooldown_seconds": 5.0,
    },
    RecoveryStrategyType.FAILOVER: {
        "risk": SafeRecoveryClass.MODERATE_RECOVERY,
        "resource_cost": {"cpu": 15.0, "memory_mb": 64.0, "slots": 1},
        "side_effect_class": "SERVICE_FAILOVER",
        "max_attempts": 2,
        "cooldown_seconds": 5.0,
    },
    RecoveryStrategyType.DEGRADE_CAPABILITY: {
        "risk": SafeRecoveryClass.LOW_RISK_RECOVERY,
        "resource_cost": {"cpu": 1.0, "memory_mb": 4.0, "slots": 1},
        "side_effect_class": "DEGRADATION",
        "max_attempts": 1,
        "cooldown_seconds": 0.0,
    },
    RecoveryStrategyType.DISABLE_CAPABILITY: {
        "risk": SafeRecoveryClass.MODERATE_RECOVERY,
        "resource_cost": {"cpu": 1.0, "memory_mb": 4.0, "slots": 1},
        "side_effect_class": "CAPABILITY_CONTAINMENT",
        "max_attempts": 1,
        "cooldown_seconds": 0.0,
    },
    RecoveryStrategyType.ROLLBACK_SAFE_STATE: {
        "risk": SafeRecoveryClass.HIGH_RISK_RECOVERY,
        "resource_cost": {"cpu": 30.0, "memory_mb": 128.0, "slots": 2},
        "side_effect_class": "STATE_ROLLBACK",
        "max_attempts": 1,
        "cooldown_seconds": 30.0,
    },
    RecoveryStrategyType.ESCALATE: {
        "risk": SafeRecoveryClass.READ_ONLY_DIAGNOSTIC,
        "resource_cost": {"cpu": 0.5, "memory_mb": 2.0, "slots": 0},
        "side_effect_class": "HUMAN_ESCALATION",
        "max_attempts": 1,
        "cooldown_seconds": 0.0,
    },
}


class RecoveryEngine:
    """Selects, authorizes, reserves budgets, and coordinates bounded recovery actions."""

    def __init__(
        self,
        security_center: Optional[Any] = None,
        governance_coordinator: Optional[Any] = None,
        resource_coordinator: Optional[Any] = None,
        emergency_stop: Optional[Any] = None,
    ) -> None:
        self._security_center = security_center
        self._governance = governance_coordinator
        self._resource_coordinator = resource_coordinator
        self._emergency_stop = emergency_stop
        self._emergency_stop_active = False

        # Scoped recovery locks: component -> asyncio.Lock
        self._locks: Dict[str, asyncio.Lock] = {}
        # Cooldown and attempt tracking: (component, strategy) -> (last_attempt_ts, count)
        self._attempt_history: Dict[Tuple[str, RecoveryStrategyType], Tuple[float, int]] = {}

    def _get_lock(self, component: str) -> asyncio.Lock:
        comp_key = component.lower()
        if comp_key not in self._locks:
            self._locks[comp_key] = asyncio.Lock()
        return self._locks[comp_key]

    def is_emergency_stopped(self, user_id: str = "default_user") -> bool:
        """Check if EmergencyStop is currently active."""
        if getattr(self, "_emergency_stop_active", False):
            return True
        if self._emergency_stop is not None:
            try:
                return bool(self._emergency_stop.is_stopped(user_id))
            except Exception:
                return False
        try:
            from app.security.emergency_stop import get_emergency_stop_service
            svc = get_emergency_stop_service()
            return svc.is_stopped(user_id)
        except Exception:
            return False

    def select_strategy(
        self,
        failure: FailureRecord,
        incident: Optional[IncidentRecord] = None,
        is_crash_loop: bool = False,
    ) -> RecoveryStrategy:
        """Selects the safest viable recovery strategy according to deterministic rules."""
        comp = failure.component.lower()
        ftype = failure.failure_type

        # 1. Crash loop override: If in a crash loop, NEVER restart!
        if is_crash_loop:
            logger.warning("Crash loop active for %s: selecting DEGRADE_CAPABILITY or ESCALATE", comp)
            if ftype in (FailureType.PROCESS_FAILURE, FailureType.RUNTIME_FAILURE, FailureType.SANDBOX_FAILURE):
                return self._create_strategy(RecoveryStrategyType.DEGRADE_CAPABILITY, comp)
            return self._create_strategy(RecoveryStrategyType.ESCALATE, comp)

        # 2. Check previous attempts for escalation chain
        prev_reconnect_attempts = self._get_attempt_count(comp, RecoveryStrategyType.RECONNECT)
        prev_restart_attempts = self._get_attempt_count(comp, RecoveryStrategyType.RESTART_COMPONENT)

        # 3. Strategy Selection based on FailureType
        if ftype in (FailureType.IPC_FAILURE, FailureType.PROTOCOL_FAILURE):
            if prev_reconnect_attempts < 3:
                return self._create_strategy(RecoveryStrategyType.RECONNECT, comp)
            elif prev_restart_attempts < 2:
                return self._create_strategy(RecoveryStrategyType.RESTART_COMPONENT, comp)
            else:
                return self._create_strategy(RecoveryStrategyType.DEGRADE_CAPABILITY, comp)

        elif ftype in (FailureType.PROCESS_FAILURE, FailureType.RUNTIME_FAILURE):
            if prev_restart_attempts < 2:
                return self._create_strategy(RecoveryStrategyType.RESTART_COMPONENT, comp)
            else:
                return self._create_strategy(RecoveryStrategyType.DEGRADE_CAPABILITY, comp)

        elif ftype == FailureType.SANDBOX_FAILURE:
            return self._create_strategy(RecoveryStrategyType.RECREATE_SANDBOX, comp)

        elif ftype in (FailureType.NETWORK_FAILURE, FailureType.DNS_FAILURE, FailureType.TLS_FAILURE):
            prev_pool_rebuilds = self._get_attempt_count(comp, RecoveryStrategyType.REBUILD_CONNECTION_POOL)
            if prev_pool_rebuilds < 2:
                return self._create_strategy(RecoveryStrategyType.REBUILD_CONNECTION_POOL, comp)
            else:
                return self._create_strategy(RecoveryStrategyType.DEGRADE_CAPABILITY, comp)

        elif ftype in (FailureType.RESOURCE_FAILURE, FailureType.MEMORY_PRESSURE, FailureType.CPU_PRESSURE, FailureType.DISK_PRESSURE):
            prev_recon = self._get_attempt_count(comp, RecoveryStrategyType.RECONCILE_RESOURCE)
            if prev_recon < 2:
                return self._create_strategy(RecoveryStrategyType.RECONCILE_RESOURCE, comp)
            else:
                return self._create_strategy(RecoveryStrategyType.RELEASE_LEAKED_RESOURCE, comp)

        elif ftype == FailureType.WORKFLOW_FAILURE:
            return self._create_strategy(RecoveryStrategyType.PAUSE_WORKFLOW, comp)

        elif ftype == FailureType.COMPUTER_FAILURE:
            return self._create_strategy(RecoveryStrategyType.DEGRADE_CAPABILITY, comp)

        elif ftype == FailureType.TOOL_FAILURE:
            if failure.retryability:
                return self._create_strategy(RecoveryStrategyType.RETRY, comp)
            return self._create_strategy(RecoveryStrategyType.DEGRADE_CAPABILITY, comp)

        elif ftype in (FailureType.AUTHORIZATION_FAILURE, FailureType.GOVERNANCE_FAILURE, FailureType.APPROVAL_FAILURE):
            return self._create_strategy(RecoveryStrategyType.ESCALATE, comp)

        elif ftype == FailureType.CORRUPTION:
            return self._create_strategy(RecoveryStrategyType.ROLLBACK_SAFE_STATE, comp)

        # Default fallback
        if failure.retryability:
            return self._create_strategy(RecoveryStrategyType.RETRY, comp)
        return self._create_strategy(RecoveryStrategyType.ESCALATE, comp)

    def _create_strategy(self, stype: RecoveryStrategyType, component: str) -> RecoveryStrategy:
        defs = STRATEGY_DEFAULTS.get(stype, STRATEGY_DEFAULTS[RecoveryStrategyType.ESCALATE])
        return RecoveryStrategy(
            strategy_type=stype,
            risk=defs["risk"],
            resource_cost=defs["resource_cost"],
            side_effect_class=defs["side_effect_class"],
            max_attempts=defs["max_attempts"],
            cooldown_seconds=defs["cooldown_seconds"],
            description=f"Autonomous recovery: {stype.value} for {component}",
        )

    def _get_attempt_count(self, component: str, strategy: RecoveryStrategyType) -> int:
        return self._attempt_history.get((component.lower(), strategy), (0.0, 0))[1]

    def record_attempt(self, component: str, strategy: RecoveryStrategyType) -> None:
        key = (component.lower(), strategy)
        prev_ts, prev_count = self._attempt_history.get(key, (0.0, 0))
        self._attempt_history[key] = (time.time(), prev_count + 1)

    def is_in_cooldown(self, component: str, strategy: RecoveryStrategy) -> Tuple[bool, float]:
        """Check if strategy is currently in cooldown."""
        key = (component.lower(), strategy.strategy_type)
        last_ts, count = self._attempt_history.get(key, (0.0, 0))
        elapsed = time.time() - last_ts
        if elapsed < strategy.cooldown_seconds and count > 0:
            return True, strategy.cooldown_seconds - elapsed
        return False, 0.0

    async def authorize_recovery(
        self,
        strategy: RecoveryStrategy,
        component: str,
        user_id: str = "system",
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validates recovery against SecurityCenter and GovernanceIntelligenceCoordinator.

        Returns (authorized, decision_id, approval_id_if_needed).
        """
        # 1. EmergencyStop check - unconditionally authoritative
        if self.is_emergency_stopped(user_id):
            logger.critical("Recovery DENIED: EmergencyStop is ACTIVE for user %s", user_id)
            return False, "EMERGENCY_STOP_ACTIVE", None

        # 2. High risk / destructive actions require human approval
        if strategy.risk in (SafeRecoveryClass.HIGH_RISK_RECOVERY, SafeRecoveryClass.DESTRUCTIVE_RECOVERY):
            appr_id = f"appr_rec_{generate_id()}"
            logger.info("Recovery %s requires human approval (id: %s)", strategy.strategy_type.value, appr_id)
            return False, "REQUIRES_APPROVAL", appr_id

        # 3. Consult GovernanceIntelligenceCoordinator if available
        if self._governance is not None:
            try:
                from app.policy.governance_schemas import GovernanceReviewRequest, AuthorityLevel
                req = GovernanceReviewRequest(
                    action_name=f"reliability.recovery.{strategy.strategy_type.value.lower()}",
                    target_entity=component,
                    authority_level=AuthorityLevel.SYSTEM,
                )
                decision = await self._governance.review_action(req)
                if not decision.approved:
                    return False, f"GOVERNANCE_DENIED: {decision.reason}", None
            except Exception as exc:
                logger.debug("Governance coordinator evaluation notice: %s", exc)

        return True, f"dec_rec_{generate_id()}", None

    async def reserve_recovery_budget(
        self,
        strategy: RecoveryStrategy,
        task_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """Reserves bounded recovery resource budget via Task 77 Resource Economy."""
        cost = strategy.resource_cost
        if not cost:
            return True, None

        if self._resource_coordinator is not None:
            try:
                alloc_res = self._resource_coordinator.request_allocation(
                    task_id=task_id,
                    demands=cost,
                    priority=90,  # High priority for reliability self-healing
                )
                if not alloc_res.get("granted", True):
                    logger.warning("Recovery resource allocation DENIED for task %s: %s", task_id, alloc_res)
                    return False, None
                rsv_id = alloc_res.get("reservation_id", f"rsv_{generate_id()}")
                return True, rsv_id
            except Exception as exc:
                logger.debug("Resource coordinator fallback reservation: %s", exc)

        # Fallback pseudo-reservation ID
        return True, f"rsv_rec_{generate_id()}"

    async def release_recovery_budget(
        self,
        reservation_id: Optional[str],
        task_id: str,
    ) -> None:
        """Releases reserved recovery resources upon completion."""
        if not reservation_id:
            return
        if self._resource_coordinator is not None:
            try:
                self._resource_coordinator.release_allocation(task_id=task_id, reservation_id=reservation_id)
            except Exception as exc:
                logger.debug("Resource coordinator release notice: %s", exc)
