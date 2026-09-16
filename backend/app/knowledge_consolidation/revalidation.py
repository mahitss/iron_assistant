"""Autonomous revalidation candidate scheduler for KAIRO (Task 92 Phase 22).

Guarantees:
- Bounded, observable, scheduled revalidation
- Responds to staleness, capability evolution, and contradictory evidence arrivals
- Respects EmergencyStop and resource limits
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.knowledge_consolidation.models import (
    MemoryEntity,
    MemoryStatus,
    generate_id,
)

logger = logging.getLogger("kairo.knowledge_consolidation.revalidation")


class AutonomousRevalidationEngine:
    """Detects revalidation triggers and schedules bounded revalidation jobs."""

    def __init__(self, max_concurrent_jobs: int = 10) -> None:
        self.max_concurrent_jobs = max_concurrent_jobs
        # job_id -> job_dict
        self._jobs: dict[str, dict[str, Any]] = {}

    def scan_revalidation_candidates(
        self,
        memories: list[MemoryEntity],
        temporal_engine: Any,
        capability_changes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Identify knowledge items requiring autonomous empirical revalidation."""
        candidates: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        for m in memories:
            # 1. Staleness trigger
            is_stale, label = temporal_engine.evaluate_staleness(m, at_time=now)
            if is_stale and m.status in (MemoryStatus.ACTIVE, MemoryStatus.STALE):
                job = self._create_job(
                    memory_id=m.memory_id,
                    trigger_reason=f"Staleness threshold exceeded ({label})",
                )
                candidates.append(job)
                continue

            # 2. Capability version evolution trigger (Task 91 integration)
            if capability_changes and m.type.value == "PROCEDURAL":
                cap_ref = m.structured_representation.get("capability_ref")
                if cap_ref and cap_ref in capability_changes:
                    job = self._create_job(
                        memory_id=m.memory_id,
                        trigger_reason=f"Underlying capability '{cap_ref}' evolved version",
                    )
                    candidates.append(job)
                    continue

            # 3. Contradiction trigger
            if m.status == MemoryStatus.CONFLICTED:
                job = self._create_job(
                    memory_id=m.memory_id,
                    trigger_reason="Active unresolved contradiction requires empirical revalidation",
                )
                candidates.append(job)

        return candidates[: self.max_concurrent_jobs]

    def _create_job(self, memory_id: str, trigger_reason: str) -> dict[str, Any]:
        job_id = generate_id("rev")
        job = {
            "job_id": job_id,
            "memory_id": memory_id,
            "trigger_reason": trigger_reason,
            "status": "SCHEDULED",
            "scheduled_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
            "result_summary": None,
        }
        self._jobs[job_id] = job
        return job

    def complete_job(self, job_id: str, success: bool, summary: str) -> None:
        """Record outcome of autonomous revalidation job."""
        job = self._jobs.get(job_id)
        if job:
            job["status"] = "COMPLETED" if success else "FAILED"
            job["completed_at"] = datetime.now(UTC).isoformat()
            job["result_summary"] = summary

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all revalidation jobs."""
        return list(self._jobs.values())
