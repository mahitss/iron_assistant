"""Execution failure modeling, transparent causality, and bounded retry policies (INVARIANTS 50-57)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.metacognition.schemas import (
    ExecutionFailureSchema,
    FailureCertainty,
    FailureType,
)


class FailureClassifier:
    """Manages failure records, ensures root causes are not fabricated, and guards against infinite retries."""

    def __init__(self, default_max_retries: int = 3) -> None:
        # failure_id -> ExecutionFailureSchema
        self._failures: Dict[str, ExecutionFailureSchema] = {}
        self.default_max_retries = default_max_retries

    def record_failure(
        self,
        action: str,
        failure_type: FailureType,
        cause: Optional[str],
        task_id: Optional[str] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        certainty: FailureCertainty = FailureCertainty.KNOWN,
        recoverability: str = "RECOVERABLE",
    ) -> ExecutionFailureSchema:
        """INVARIANT 53 & 54: Transparent failure recording; if cause is uncertain, marks UNCERTAIN rather than inventing reasons."""
        f_id = str(uuid.uuid4())
        clean_cause = cause.strip() if cause else "Root cause UNCERTAIN (investigation pending)"
        if not cause:
            certainty = FailureCertainty.UNKNOWN

        rec = ExecutionFailureSchema(
            failure_id=f_id,
            task_id=task_id,
            action=action,
            failure_type=failure_type,
            certainty=certainty,
            cause=clean_cause,
            evidence=evidence or [],
            recoverability=recoverability,
            retry_count=0,
            max_retries=self.default_max_retries,
            timestamp=datetime.now(UTC),
        )
        self._failures[f_id] = rec
        return rec

    def can_retry(self, failure_id: str) -> bool:
        """INVARIANT 56 & 57: Retry only when safe and within budget; prevent infinite retries."""
        fail = self._failures.get(failure_id)
        if not fail:
            return False

        if fail.recoverability == "NON_RECOVERABLE":
            return False

        # Non-retryable types
        if fail.failure_type in (FailureType.AUTH_FAILURE.value, FailureType.POLICY_BLOCK.value):
            return False

        return fail.retry_count < fail.max_retries

    def increment_retry(self, failure_id: str) -> int:
        fail = self._failures.get(failure_id)
        if not fail:
            raise ValueError(f"Failure '{failure_id}' not found.")
        fail.retry_count += 1
        return fail.retry_count

    def get_failure(self, failure_id: str) -> Optional[ExecutionFailureSchema]:
        return self._failures.get(failure_id)

    def list_failures(self, task_id: Optional[str] = None) -> List[ExecutionFailureSchema]:
        fails = list(self._failures.values())
        if task_id:
            fails = [f for f in fails if f.task_id == task_id]
        return fails
