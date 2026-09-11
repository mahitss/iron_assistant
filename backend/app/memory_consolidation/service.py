"""Unified Service Facade for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Coordinates capture, lifecycle transitions, deduplication, autonomous consolidation,
contradiction management, temporal validity, forgetting, and explainable retrieval.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.memory_consolidation.capture import MemoryCapturePipeline
from app.memory_consolidation.consolidation import AutonomousConsolidationEngine
from app.memory_consolidation.contradictions import ContradictionEngine
from app.memory_consolidation.deduplication import DeduplicationEngine
from app.memory_consolidation.forgetting import ForgettingEngine
from app.memory_consolidation.integrator import MemorySubsystemIntegrator
from app.memory_consolidation.lifecycle import MemoryLifecycleStateMachine
from app.memory_consolidation.privacy import MemoryPrivacyGuard
from app.memory_consolidation.provenance import ProvenanceTracker
from app.memory_consolidation.retrieval import MemoryRetrievalEngine
from app.memory_consolidation.schemas import (
    ConsolidationCandidate,
    ContextAssemblyRequest,
    ContextAssemblyResult,
    ContradictionReport,
    ContradictionStatus,
    DurableMemory,
    FreshnessState,
    MemoryAuditEventType,
    MemoryCaptureRequest,
    MemoryHealthMetrics,
    MemoryLifecycleState,
    MemoryProvenance,
    MemorySearchRequest,
    MemorySearchResult,
    TrustLevel,
)
from app.memory_consolidation.temporal import TemporalValidityEngine
from app.memory_consolidation.worker import AutonomousConsolidationWorker

logger = logging.getLogger("kairo.memory_consolidation.service")


class MemoryConsolidationService:
    """Enterprise domain service orchestrating memory consolidation and lifecycle management."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        # In-memory store for high-performance retrieval and testing continuity
        self._memories: dict[str, DurableMemory] = {}
        self._provenances: dict[str, MemoryProvenance] = {}
        self._conflicts: dict[str, ContradictionReport] = {}
        self._candidates: dict[str, ConsolidationCandidate] = {}
        self._audit_logs: list[dict[str, Any]] = []

    # --------------------------------------------------------------------------
    # 1. Capture & Ingestion (Spec 6)
    # --------------------------------------------------------------------------

    def capture(self, request: MemoryCaptureRequest, tenant_id: str = "default") -> DurableMemory:
        """Process incoming observation, event, claim, or experience."""
        request.tenant_id = tenant_id
        memory, provenance, audits = MemoryCapturePipeline.process_capture(request)

        # Check for duplicates against existing active memories
        existing = [m for m in self._memories.values() if m.tenant_id == tenant_id]
        dup_match, score, match_type = DeduplicationEngine.find_duplicate(memory.content, existing)

        if dup_match is not None and score >= 0.95:
            # Canonicalize duplicate reference
            DeduplicationEngine.merge_references_into_canonical(
                dup_match,
                duplicate_source_ref=memory.memory_id,
                is_independent_source=provenance.is_independent_source,
            )
            audits.append(
                {
                    "audit_id": f"maud_dup_{memory.memory_id[:8]}",
                    "memory_id": dup_match.memory_id,
                    "tenant_id": tenant_id,
                    "event_type": MemoryAuditEventType.MEMORY_DEDUPLICATED.value,
                    "actor": "deduplication_engine",
                    "previous_state": dup_match.status.value,
                    "new_state": dup_match.status.value,
                    "reason": f"Deduplicated incoming memory {memory.memory_id} (match={match_type}, score={score:.2f})",
                    "details": {"incoming_id": memory.memory_id, "score": score},
                    "timestamp": datetime.now(UTC),
                }
            )
            self._audit_logs.extend(audits)
            return dup_match

        # Store memory, provenance, and audit logs
        self._memories[memory.memory_id] = memory
        self._provenances[memory.memory_id] = provenance
        self._audit_logs.extend(audits)

        # Immediate contradiction check against existing active memories
        for other in existing:
            if other.status == MemoryLifecycleState.ACTIVE:
                conflict = ContradictionEngine.analyze_conflict(memory, other)
                if conflict is not None:
                    self._conflicts[conflict.conflict_id] = conflict
                    self._audit_logs.append(
                        {
                            "audit_id": f"maud_cnf_{conflict.conflict_id[:8]}",
                            "memory_id": memory.memory_id,
                            "tenant_id": tenant_id,
                            "event_type": MemoryAuditEventType.MEMORY_CONFLICT_DETECTED.value,
                            "actor": "contradiction_engine",
                            "previous_state": memory.status.value,
                            "new_state": memory.status.value,
                            "reason": conflict.explanation,
                            "details": {"competing_memory_id": other.memory_id},
                            "timestamp": datetime.now(UTC),
                        }
                    )

        return memory

    # --------------------------------------------------------------------------
    # 2. Retrieval & Context Assembly (Spec 20, 21, 22)
    # --------------------------------------------------------------------------

    def search(self, request: MemorySearchRequest, tenant_id: str = "default") -> list[MemorySearchResult]:
        """Explainable multi-factor search with tenant isolation."""
        tenant_memories = [m for m in self._memories.values() if m.tenant_id == tenant_id]
        return MemoryRetrievalEngine.search(tenant_memories, request)

    def assemble_context(
        self, request: ContextAssemblyRequest, tenant_id: str = "default"
    ) -> ContextAssemblyResult:
        """Construct bounded, partitioned task context for cognitive agents (Spec 22)."""
        request.tenant_id = tenant_id
        tenant_memories = [m for m in self._memories.values() if m.tenant_id == tenant_id]
        return MemoryRetrievalEngine.assemble_context(tenant_memories, request)

    # --------------------------------------------------------------------------
    # 3. Individual Memory Inspection & Provenance (Spec 7, 25)
    # --------------------------------------------------------------------------

    def get_memory(self, memory_id: str, tenant_id: str = "default") -> DurableMemory:
        """Retrieve memory record enforcing tenant isolation."""
        if memory_id not in self._memories:
            raise KeyError(f"Memory '{memory_id}' not found.")
        mem = self._memories[memory_id]
        MemoryPrivacyGuard.verify_tenant_access(mem.tenant_id, tenant_id, memory_id)
        TemporalValidityEngine.refresh_memory_temporal_state(mem)
        return mem

    def get_provenance(self, memory_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve explainable lineage graph for memory."""
        mem = self.get_memory(memory_id, tenant_id=tenant_id)
        prov = self._provenances.get(memory_id, mem.provenance)
        return ProvenanceTracker.build_provenance_summary(prov)

    def get_history(self, memory_id: str, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Retrieve chronological audit trail of memory lifecycle operations."""
        self.get_memory(memory_id, tenant_id=tenant_id)  # verify existence & tenant
        return [
            log
            for log in self._audit_logs
            if log.get("memory_id") == memory_id and log.get("tenant_id") == tenant_id
        ]

    # --------------------------------------------------------------------------
    # 4. Lifecycle Operations: Validate, Promote, Quarantine, Forget (Spec 5, 11, 16)
    # --------------------------------------------------------------------------

    def validate_memory(
        self, memory_id: str, verified: bool, evidence_ref: str, tenant_id: str = "default"
    ) -> DurableMemory:
        """Apply empirical verification outcome (Task 42 integration)."""
        mem = self.get_memory(memory_id, tenant_id=tenant_id)
        MemorySubsystemIntegrator.apply_verification_outcome(mem, verified, evidence_ref)
        audit = MemoryLifecycleStateMachine.transition(
            mem,
            target_state=MemoryLifecycleState.ACTIVE,
            actor="verifier",
            reason=f"Verification outcome: verified={verified}, ref={evidence_ref}",
        )
        self._audit_logs.append(audit)
        return mem

    def promote_memory(self, memory_id: str, reason: str, tenant_id: str = "default") -> DurableMemory:
        """Promote memory to executive tier (Spec 11, Task 53 integration)."""
        mem = self.get_memory(memory_id, tenant_id=tenant_id)
        MemorySubsystemIntegrator.promote_to_executive(mem, reason)
        audit = MemoryLifecycleStateMachine.transition(
            mem,
            target_state=MemoryLifecycleState.PROMOTED,
            actor="promotion_policy",
            reason=reason,
        )
        self._audit_logs.append(audit)
        return mem

    def quarantine_memory(self, memory_id: str, reason: str, tenant_id: str = "default") -> DurableMemory:
        """Quarantine suspicious or unverified high-risk memory (Spec 17)."""
        mem = self.get_memory(memory_id, tenant_id=tenant_id)
        mem.trust_level = TrustLevel.QUARANTINED
        audit = MemoryLifecycleStateMachine.transition(
            mem,
            target_state=MemoryLifecycleState.QUARANTINED,
            actor="safety_engine",
            reason=reason,
        )
        self._audit_logs.append(audit)
        return mem

    def forget_memory(
        self, memory_id: str, reason: str, tenant_id: str = "default", hard_delete: bool = False
    ) -> DurableMemory:
        """Execute policy-based or user-requested forgetting with tombstoning (Spec 16)."""
        mem = self.get_memory(memory_id, tenant_id=tenant_id)
        _, tombstone_audit, _ = ForgettingEngine.execute_forgetting(
            mem, reason=reason, hard_delete=hard_delete
        )
        self._audit_logs.append(tombstone_audit)
        return mem

    # --------------------------------------------------------------------------
    # 5. Consolidation & Workers (Spec 9, 26)
    # --------------------------------------------------------------------------

    def consolidate_explicit(
        self, memory_ids: list[str], tenant_id: str = "default"
    ) -> tuple[ConsolidationCandidate, DurableMemory]:
        """Manually trigger consolidation over an explicit list of memories."""
        cluster = [self.get_memory(mid, tenant_id=tenant_id) for mid in memory_ids]
        candidate, consolidated = AutonomousConsolidationEngine.consolidate_cluster(
            cluster, tenant_id=tenant_id, actor="explicit_api"
        )
        self._candidates[candidate.candidate_id] = candidate
        self._memories[consolidated.memory_id] = consolidated
        self._provenances[consolidated.memory_id] = consolidated.provenance

        for m in cluster:
            m.status = MemoryLifecycleState.CONSOLIDATED

        self._audit_logs.append(
            {
                "audit_id": f"maud_{consolidated.memory_id[:8]}",
                "memory_id": consolidated.memory_id,
                "tenant_id": tenant_id,
                "event_type": MemoryAuditEventType.MEMORY_CONSOLIDATED.value,
                "actor": "consolidation_api",
                "previous_state": None,
                "new_state": MemoryLifecycleState.CONSOLIDATED.value,
                "reason": f"Consolidated {len(memory_ids)} source memories",
                "details": {"source_ids": memory_ids, "candidate_id": candidate.candidate_id},
                "timestamp": datetime.now(UTC),
            }
        )
        return candidate, consolidated

    def run_sweep(self, tenant_id: str = "default") -> dict[str, Any]:
        """Run autonomous worker sweep."""
        worker = AutonomousConsolidationWorker(tenant_id=tenant_id)
        tenant_memories = [m for m in self._memories.values() if m.tenant_id == tenant_id]
        return worker.run_sweep(tenant_memories)

    # --------------------------------------------------------------------------
    # 6. Operational Queries: Conflicts, Stale, Expiring, Health (Spec 12, 14, 27)
    # --------------------------------------------------------------------------

    def get_conflicts(self, tenant_id: str = "default") -> list[ContradictionReport]:
        """List active contradictions and competing claims (Spec 12)."""
        return [
            c
            for c in self._conflicts.values()
            if c.tenant_id == tenant_id and c.status == ContradictionStatus.CONFLICTED
        ]

    def get_stale(self, tenant_id: str = "default") -> list[DurableMemory]:
        """List memories that have exceeded their type-specific TTL (Spec 14)."""
        now = datetime.now(UTC)
        stale: list[DurableMemory] = []
        for m in self._memories.values():
            if m.tenant_id == tenant_id:
                if TemporalValidityEngine.evaluate_freshness(m, reference_time=now) in {
                    FreshnessState.STALE,
                    FreshnessState.EXPIRED,
                }:
                    stale.append(m)
        return stale

    def get_expiring(self, tenant_id: str = "default", within_hours: int = 24) -> list[DurableMemory]:
        """List memories scheduled to expire within the given time horizon."""
        now = datetime.now(UTC)
        horizon = now + timedelta(hours=within_hours)
        expiring: list[DurableMemory] = []
        for m in self._memories.values():
            if m.tenant_id == tenant_id and m.expires_at:
                if now <= m.expires_at <= horizon:
                    expiring.append(m)
        return expiring

    def get_health(self, tenant_id: str = "default") -> MemoryHealthMetrics:
        """Calculate comprehensive operational memory health telemetry (Spec 27)."""
        now = datetime.now(UTC)
        tenant_mems = [m for m in self._memories.values() if m.tenant_id == tenant_id]

        total = len(tenant_mems)
        by_type: dict[str, int] = {}
        active = 0
        quarantined = 0
        conflicted = 0
        stale = 0
        expired = 0
        poisoning_count = 0
        total_age_seconds = 0.0

        for m in tenant_mems:
            t_val = m.memory_type.value
            by_type[t_val] = by_type.get(t_val, 0) + 1

            if m.status == MemoryLifecycleState.ACTIVE:
                active += 1
            elif m.status == MemoryLifecycleState.QUARANTINED:
                quarantined += 1
                if m.trust_level == TrustLevel.QUARANTINED:
                    poisoning_count += 1
            elif m.status == MemoryLifecycleState.CONFLICTED:
                conflicted += 1

            freshness = TemporalValidityEngine.evaluate_freshness(m, reference_time=now)
            if freshness == FreshnessState.STALE:
                stale += 1
            elif freshness == FreshnessState.EXPIRED:
                expired += 1

            total_age_seconds += (now - m.created_at).total_seconds()

        avg_age_hours = round(total_age_seconds / (max(total, 1) * 3600), 2)
        consolidated_count = sum(1 for m in tenant_mems if m.status == MemoryLifecycleState.CONSOLIDATED)
        promoted_count = sum(1 for m in tenant_mems if m.status == MemoryLifecycleState.PROMOTED)

        return MemoryHealthMetrics(
            total_memories=total,
            memories_by_type=by_type,
            active_count=active,
            quarantined_count=quarantined,
            conflicted_count=conflicted,
            stale_count=stale,
            expired_count=expired,
            promotion_rate=round(promoted_count / max(total, 1), 3),
            consolidation_rate=round(consolidated_count / max(total, 1), 3),
            deduplication_rate=0.0,
            retrieval_hit_rate=1.0,
            average_age_hours=avg_age_hours,
            poisoning_detections_count=poisoning_count,
            tenant_id=tenant_id,
            calculated_at=now,
        )


# Global singleton instance
memory_consolidation_service = MemoryConsolidationService()
