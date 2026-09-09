"""Central coordinator for Kairo Resilience, Fault-Tolerance, and Recovery (Task 37)."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import logging
from typing import Any, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.checkpoint import ResilienceCheckpointManager
from app.resilience.circuit_breaker import CircuitBreakerRegistry
from app.resilience.degradation import DegradationManager
from app.resilience.dedupe import EventDedupeManager
from app.resilience.failures import ErrorSanitizer, FailureClassifier
from app.resilience.fallback import FallbackRouter
from app.resilience.health import DependencyHealthTracker
from app.resilience.idempotency import IdempotencyManager
from app.resilience.leases import LeaseManager
from app.resilience.outbox import OutboxBridge
from app.resilience.reconciliation import OutcomeReconciler
from app.resilience.recovery import TaskRecoveryManager
from app.resilience.retry import RetryManager
from app.resilience.schemas import (
    CircuitBreakerConfig,
    Failure,
    FailureCategory,
    OutcomeState,
    RecoveryState,
    RetryBudget,
    RetryPolicy,
    SideEffectType,
    SystemReliabilityDashboard,
    TaskCheckpoint,
    TaskLease,
    utc_now,
)
from app.resilience.timeout import DeadlineManager
from app.resilience.watchdog import QuarantineManager, TaskWatchdog

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ResilienceManager:
    """Unified coordinator managing resilience, recovery, leases, circuits, and graceful degradation."""

    def __init__(self) -> None:
        self.circuit_registry = CircuitBreakerRegistry()
        self.retry_mgr = RetryManager()
        self.idempotency_mgr = IdempotencyManager()
        self.reconciler = OutcomeReconciler()
        self.lease_mgr = LeaseManager()
        self.quarantine_mgr = QuarantineManager()
        self.watchdog = TaskWatchdog(self.quarantine_mgr)
        self.checkpoint_mgr = ResilienceCheckpointManager()
        self.recovery_mgr = TaskRecoveryManager(
            checkpoint_mgr=self.checkpoint_mgr,
            lease_mgr=self.lease_mgr,
            quarantine_mgr=self.quarantine_mgr,
        )
        self.fallback_router = FallbackRouter(self.circuit_registry)
        self.degradation_mgr = DegradationManager()
        self.health_tracker = DependencyHealthTracker()
        self.dedupe_mgr = EventDedupeManager()
        self.outbox_bridge = OutboxBridge()

    async def execute_resilient_operation(
        self,
        func: Callable[[], Awaitable[T]],
        operation: str,
        component: str,
        side_effect_type: SideEffectType = SideEffectType.READ_ONLY,
        circuit_id: str | None = None,
        idempotency_key: str | None = None,
        user_id: str | None = None,
        task_id: str | None = None,
        timeout_seconds: float | None = 30.0,
        deadline_mgr: DeadlineManager | None = None,
        retry_policy: RetryPolicy | None = None,
        retry_budget: RetryBudget | None = None,
        correlation_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> T:
        """High-level resilient execution wrapper uniting timeouts, circuits, degradation, idempotency, and retries."""
        # 1. Degradation check: Block writes in read-only mode
        self.degradation_mgr.check_operation_permitted(side_effect_type)

        # 2. Idempotency Check for side-effecting operations
        is_new = True
        if idempotency_key:
            is_new, prior_rec = await self.idempotency_mgr.begin_operation(
                key=idempotency_key,
                operation=operation,
                user_id=user_id,
                task_id=task_id,
                session=session,
            )
            if not is_new and prior_rec and prior_rec.status == "COMPLETED":
                logger.info("Resilience: Returning cached result for idempotency key %s", idempotency_key)
                return prior_rec.result_reference.get("value") if prior_rec.result_reference else None  # type: ignore

        # 3. Deadline derivation
        effective_deadline = deadline_mgr or DeadlineManager(timeout_seconds=timeout_seconds)

        # 4. Define inner execution under circuit breaker and timeout
        async def _run_once() -> T:
            async def _timed_call() -> T:
                return await effective_deadline.execute_with_deadline(
                    func=func,
                    operation=operation,
                    desired_timeout_seconds=timeout_seconds,
                )

            if circuit_id:
                return await self.circuit_registry.execute(circuit_id, _timed_call)
            return await _timed_call()

        # 5. Execute with Bounded Retries
        is_retry_safe = (side_effect_type == SideEffectType.READ_ONLY or side_effect_type == SideEffectType.IDEMPOTENT_WRITE)
        try:
            result = await self.retry_mgr.execute_with_retry(
                func=_run_once,
                operation=operation,
                component=component,
                policy=retry_policy,
                budget=retry_budget,
                is_retry_safe=is_retry_safe,
                correlation_id=correlation_id,
            )

            # Mark idempotency completed if used
            if idempotency_key:
                ref = {"value": result} if isinstance(result, (int, str, float, bool, dict, list)) else {"status": "ok"}
                await self.idempotency_mgr.complete_operation(idempotency_key, result_reference=ref, session=session)

            return result
        except Exception as exc:
            if idempotency_key:
                await self.idempotency_mgr.fail_operation(idempotency_key, session=session)
            raise exc

    def get_reliability_dashboard(self) -> SystemReliabilityDashboard:
        """Aggregates real-time resilience status for UI and observability."""
        circuits = self.circuit_registry.list_all()
        dependencies = self.health_tracker.get_all_reports()

        total_r = self.retry_mgr.total_retries
        ret_succ = self.retry_mgr.retry_successes
        ret_rate = (ret_succ / total_r) if total_r > 0 else 1.0

        total_rec = self.recovery_mgr.recovery_successes + self.recovery_mgr.recovery_failures
        rec_rate = (self.recovery_mgr.recovery_successes / total_rec) if total_rec > 0 else 1.0

        return SystemReliabilityDashboard(
            dependencies=dependencies,
            circuits=circuits,
            active_leases=len(self.lease_mgr._memory_leases),
            quarantined_tasks_count=len([q for q in self.quarantine_mgr._memory_quarantine.values() if q.status == "QUARANTINED"]),
            total_retries=total_r,
            retry_success_rate=round(ret_rate, 3),
            recovery_success_rate=round(rec_rate, 3),
            stuck_tasks_detected=self.watchdog.stuck_tasks_detected,
        )


# Global singleton instance
resilience_manager = ResilienceManager()
