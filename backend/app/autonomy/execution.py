"""Canonical Autonomous Execution Loop, Idempotency, Unknown Outcome Recovery, and Resource Safety (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

from app.autonomy.budgets import AutonomousBudget
from app.autonomy.checkpoints import CheckpointManager
from app.autonomy.controller import RunController, StepExecutionResult
from app.autonomy.deadlines import DeadlineTracker
from app.autonomy.interruption import InterruptionHandler
from app.autonomy.progress import ProgressTracker
from app.autonomy.safety import ActionClassification, AutonomyLevel, AutonomySafetyGuard

logger = logging.getLogger("kairo.autonomy.execution")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutcomeCertainty(str, Enum):
    KNOWN_SUCCESS = "KNOWN_SUCCESS"
    KNOWN_FAILURE = "KNOWN_FAILURE"
    UNKNOWN = "UNKNOWN"  # Network dropped, timeout, partial receipt (Spec 43, 95, 97)


class DuplicateExecutionError(Exception):
    """Raised when an operation attempts to execute an already processed idempotency key (Spec 46, 47)."""


class ResourceLockConflictError(Exception):
    """Raised when concurrent operations attempt conflicting writes on the same resource (Spec 33, 34)."""


class SideEffectRetryViolationError(Exception):
    """Raised when a non-idempotent operation is retried blindly without verification (Spec 45)."""


@dataclass
class IdempotencyRecord:
    """Tracks idempotency keys and cached execution results (Spec 46, 47)."""

    idempotency_key: str
    run_id: str
    step_id: str
    payload_hash: str
    outcome: OutcomeCertainty
    cached_output: Optional[Dict[str, Any]] = None
    executed_at: datetime = field(default_factory=utc_now)


class ExecutionResourceManager:
    """Guarantees parallel execution safety and write serialization across concurrent steps (Spec 33, 34)."""

    def __init__(self) -> None:
        # resource_path -> active_holder (step_id)
        self._write_locks: Dict[str, str] = {}
        # resource_path -> set of active reader step_ids
        self._read_locks: Dict[str, Set[str]] = {}

    def acquire_lock(self, resource_path: str, step_id: str, is_write: bool = False) -> bool:
        """Acquire reader-writer lock. Conflicting writes are never parallelized (Spec 33)."""
        norm = resource_path.replace("\\", "/").lower()

        if is_write:
            # Cannot write if someone is writing or reading
            if norm in self._write_locks and self._write_locks[norm] != step_id:
                raise ResourceLockConflictError(
                    f"Resource '{resource_path}' is write-locked by active step '{self._write_locks[norm]}'."
                )
            readers = self._read_locks.get(norm, set())
            if readers and not (len(readers) == 1 and step_id in readers):
                raise ResourceLockConflictError(
                    f"Resource '{resource_path}' has active readers ({readers}); cannot acquire write lock."
                )
            self._write_locks[norm] = step_id
            return True
        else:
            # Read lock: allowed if no write lock (or write lock held by same step)
            if norm in self._write_locks and self._write_locks[norm] != step_id:
                raise ResourceLockConflictError(
                    f"Resource '{resource_path}' is write-locked by '{self._write_locks[norm]}'; read blocked."
                )
            self._read_locks.setdefault(norm, set()).add(step_id)
            return True

    def release_lock(self, resource_path: str, step_id: str) -> None:
        norm = resource_path.replace("\\", "/").lower()
        if self._write_locks.get(norm) == step_id:
            del self._write_locks[norm]
        if norm in self._read_locks:
            self._read_locks[norm].discard(step_id)
            if not self._read_locks[norm]:
                del self._read_locks[norm]


class AutonomousExecutionLoop:
    """Canonical execution loop with idempotency, unknown outcome verification, and dry-run (Spec 28, 43-47, 131-133)."""

    def __init__(
        self,
        controller: RunController,
        resource_manager: Optional[ExecutionResourceManager] = None,
        max_retries_per_step: int = 3,
        is_dry_run: bool = False,
    ) -> None:
        self.controller = controller
        self.resource_manager = resource_manager or ExecutionResourceManager()
        self.max_retries_per_step = max_retries_per_step
        self.is_dry_run = is_dry_run
        # idempotency_key -> IdempotencyRecord
        self._idempotency_store: Dict[str, IdempotencyRecord] = {}
        # step_id -> retry_count
        self._step_retry_counts: Dict[str, int] = {}

    def generate_idempotency_key(self, run_id: str, step_id: str, tool_name: str, params: Dict[str, Any]) -> str:
        """Create a deterministic idempotency key for an operation (Spec 46)."""
        raw = json.dumps({"run_id": run_id, "step_id": step_id, "tool": tool_name, "params": params}, sort_keys=True)
        return f"idemp_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

    def execute_step_safely(
        self,
        run_id: str,
        plan_version: int,
        step: Dict[str, Any],
        tool_executor_fn: Callable[[str, Dict[str, Any]], Any],
        state_inspector_fn: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        verifier_fn: Optional[Callable[[Dict[str, Any], Any], tuple[bool, str]]] = None,
        is_pre_approved: bool = False,
    ) -> StepExecutionResult:
        """Execute step with full unknown outcome recovery, idempotency check, and retry bounding (Spec 43-50)."""
        step_id = step.get("step_id", step.get("id", "step_unknown"))
        tool_name = step.get("tool_name", "noop")
        params = step.get("params", {})
        is_idempotent = step.get("is_idempotent", False)
        target_resource = step.get("target_resource", "")
        action_type = step.get("action_type", "ANALYZE").upper()
        is_write = action_type in ["WRITE", "DEPLOY", "DELETE"]

        # 1. Dry run bypass: If in dry run mode, do NOT perform real side effects (Spec 132, 133)
        if self.is_dry_run:
            logger.info("[DRY-RUN] Simulating execution of step %s (%s)", step_id, tool_name)
            return StepExecutionResult(
                step_id=step_id,
                is_success=True,
                is_verified=True,
                outputs={"simulated": True, "dry_run": True, "status": "SIMULATED_SUCCESS"},
                verification_notes="Dry run simulation - no external side effects produced.",
            )

        # 2. Check and enforce idempotency (Spec 46, 47)
        idemp_key = self.generate_idempotency_key(run_id, step_id, tool_name, params)
        if idemp_key in self._idempotency_store:
            record = self._idempotency_store[idemp_key]
            if record.outcome == OutcomeCertainty.KNOWN_SUCCESS:
                logger.info("Idempotency match on key %s; reusing verified result without re-execution", idemp_key)
                return StepExecutionResult(
                    step_id=step_id,
                    is_success=True,
                    is_verified=True,
                    outputs=record.cached_output or {},
                    verification_notes="Idempotent replay from verified cache.",
                )

        # 3. Check retry limit (Spec 49, 50)
        retries = self._step_retry_counts.get(step_id, 0)
        if retries >= self.max_retries_per_step:
            logger.error("Step %s exceeded max retries (%d); escalating to replan/diagnosis", step_id, self.max_retries_per_step)
            return StepExecutionResult(
                step_id=step_id,
                is_success=False,
                is_verified=False,
                error=f"Retry exhaustion: Step failed {retries} consecutive times. Replan required.",
            )

        # 4. Unknown outcome recovery before non-idempotent retry (Spec 43, 44, 45)
        if retries > 0 and not is_idempotent:
            # Must verify whether action occurred prior to retrying
            if state_inspector_fn:
                action_already_occurred = state_inspector_fn(target_resource, params)
                if action_already_occurred:
                    logger.warning("Unknown outcome resolved: Side-effect already took effect on %s. Re-verification succeeds.", target_resource)
                    return StepExecutionResult(
                        step_id=step_id,
                        is_success=True,
                        is_verified=True,
                        outputs={"recovered_prior_effect": True},
                        verification_notes="Verified side-effect occurred despite prior network/worker uncertainty.",
                    )
            else:
                # If cannot verify, prevent blind retry of non-idempotent destructive operation
                raise SideEffectRetryViolationError(
                    f"BLOCKED: Cannot blindly retry non-idempotent step {step_id} on {target_resource} without state verification."
                )

        # 5. Acquire resource locks (Spec 33, 34)
        if target_resource:
            self.resource_manager.acquire_lock(target_resource, step_id, is_write=is_write)

        try:
            # 6. Execute via controller
            result = self.controller.execute_step(
                run_id=run_id,
                plan_version=plan_version,
                step=step,
                tool_executor_fn=tool_executor_fn,
                verifier_fn=verifier_fn,
                is_pre_approved=is_pre_approved,
            )

            # 7. Record idempotency record if verified
            if result.is_success and result.is_verified:
                self._idempotency_store[idemp_key] = IdempotencyRecord(
                    idempotency_key=idemp_key,
                    run_id=run_id,
                    step_id=step_id,
                    payload_hash=idemp_key,
                    outcome=OutcomeCertainty.KNOWN_SUCCESS,
                    cached_output=result.outputs,
                )
            else:
                self._step_retry_counts[step_id] = retries + 1

            return result

        except Exception as exc:
            self._step_retry_counts[step_id] = retries + 1
            logger.error("Execution error on step %s: %s", step_id, exc)
            raise
        finally:
            # Release resource locks
            if target_resource:
                self.resource_manager.release_lock(target_resource, step_id)
