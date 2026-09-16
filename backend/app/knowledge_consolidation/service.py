"""Master Knowledge Consolidation and Memory Evolution Service for KAIRO (Task 92).

Orchestrates:
- Memory taxonomy, provenance, and grounding evidence
- Semantic deduplication and conflict detection/resolution
- Temporal validity and autonomous revalidation
- Context assembly with surfaced contradictions
- Forensic memory reconstruction
- SecurityCenter and EmergencyStop enforcement (Phase 24-27)
- Canonical event bus integration (Phase 29)
- Concurrency and failure recovery (Phase 33-34)
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
import threading
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import get_db, get_sessionmaker
from app.events.bus import get_event_bus
from app.events.schemas import Event
from app.knowledge_consolidation.attention_bridge import AttentionEngineBridge
from app.knowledge_consolidation.conflicts import ConflictDetectionEngine
from app.knowledge_consolidation.consolidation_engine import ConsolidationEngine
from app.knowledge_consolidation.context_assembly import ContextAssemblyEngine
from app.knowledge_consolidation.deduplication import DeduplicationEngine
from app.knowledge_consolidation.derived import DerivedKnowledgeManager
from app.knowledge_consolidation.evidence import EvidenceManager
from app.knowledge_consolidation.graph_bridge import KnowledgeGraphBridge
from app.knowledge_consolidation.hypotheses import HypothesisManager
from app.knowledge_consolidation.lifecycle import MemoryLifecycleManager
from app.knowledge_consolidation.models import (
    CertaintyState,
    ConflictResolutionRequest,
    ConflictType,
    EvidenceRelationType,
    MemoryConflict,
    MemoryEntity,
    MemoryIngestionRequest,
    MemoryReconstructionRequest,
    MemoryReconstructionResult,
    MemoryStatus,
    MemoryType,
    ProvenanceSourceType,
    RetentionAction,
    SensitivityClassification,
    VolatilityClass,
    generate_id,
)
from app.knowledge_consolidation.procedural import ProceduralMemoryManager
from app.knowledge_consolidation.provenance import ProvenanceTracker
from app.knowledge_consolidation.reconstruction import MemoryReconstructionEngine
from app.knowledge_consolidation.resolution import ConflictResolutionEngine
from app.knowledge_consolidation.retention import RetentionEngine
from app.knowledge_consolidation.revalidation import AutonomousRevalidationEngine
from app.knowledge_consolidation.temporal import TemporalKnowledgeEngine
from app.knowledge_consolidation.vector_bridge import VectorIndexBridge
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.security.exceptions import EmergencyStopActiveError, SecurityError
from app.security.permissions import PermissionLevel

logger = logging.getLogger("kairo.knowledge_consolidation.service")


class KnowledgeConsolidationService:
    """Production-grade coordinator for KAIRO autonomous knowledge consolidation and evolution."""

    def __init__(
        self,
        emergency_stop: EmergencyStopService | None = None,
        db: Session | None = None,
    ) -> None:
        self.emergency_stop = emergency_stop or get_emergency_stop_service()
        self.db = db
        self._lock = threading.RLock()

        # In-memory primary registers
        self._memories: dict[str, MemoryEntity] = {}

        # Subsystems
        self.lifecycle = MemoryLifecycleManager()
        self.provenance = ProvenanceTracker()
        self.evidence = EvidenceManager()
        self.deduplication = DeduplicationEngine()
        self.conflicts = ConflictDetectionEngine()
        self.resolution = ConflictResolutionEngine()
        self.temporal = TemporalKnowledgeEngine()
        self.retention = RetentionEngine()
        self.consolidation = ConsolidationEngine()
        self.procedural = ProceduralMemoryManager()
        self.hypotheses = HypothesisManager()
        self.derived = DerivedKnowledgeManager()
        self.graph_bridge = KnowledgeGraphBridge()
        self.vector_bridge = VectorIndexBridge()
        self.context_assembler = ContextAssemblyEngine()
        self.reconstruction = MemoryReconstructionEngine()
        self.revalidation = AutonomousRevalidationEngine()
        self.attention_bridge = AttentionEngineBridge()

    # --------------------------------------------------------------------------
    # Safety & Authority Checks
    # --------------------------------------------------------------------------

    def _verify_mutation_allowed(self, user_id: str | None = None) -> None:
        """Verify that EmergencyStop is not active for mutating operations (fail-closed)."""
        if self.emergency_stop.is_stopped(user_id):
            raise EmergencyStopActiveError("Emergency stop is ACTIVE. Autonomous memory mutations are halted.")

    def _emit_event(self, event_type: str, memory_id: str, details: dict[str, Any]) -> None:
        """Emit canonical event to KAIRO event fabric if available."""
        try:
            import asyncio
            bus = get_event_bus()
            ev = Event(
                event_type=event_type,
                source="knowledge_consolidation",
                payload={"memory_id": memory_id, **details},
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus.publish(ev))
            except RuntimeError:
                pass
        except Exception as exc:
            logger.debug("Event bus publish skipped: %s", exc)

    # --------------------------------------------------------------------------
    # Phase 6 — Memory Ingestion Pipeline
    # --------------------------------------------------------------------------

    def ingest_memory(self, request: MemoryIngestionRequest) -> MemoryEntity:
        """Execute complete normalization, deduplication, conflict check, and persistence pipeline."""
        self._verify_mutation_allowed(request.user_id)

        with self._lock:
            # 1. Deduplication Check
            existing_list = list(self._memories.values())
            duplicate, match_type = self.deduplication.find_duplicate(
                request.content, request.structured_payload, existing_list
            )

            if duplicate and match_type == "EXACT":
                # Merge into existing memory rather than creating duplicate
                merged = self.deduplication.merge_into_existing(
                    existing_memory=duplicate,
                    new_content=request.content,
                    new_source=request.source,
                    new_source_type=request.source_type,
                    evidence_manager=self.evidence,
                    new_confidence=request.confidence,
                )
                self._emit_event("memory.merged", merged.memory_id, {"merged_content": request.content[:64]})
                return merged

            # 2. Entity Construction
            now = datetime.now(UTC)
            mem_id = generate_id("mem")

            entity = MemoryEntity(
                memory_id=mem_id,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                project_id=request.project_id,
                type=request.type,
                content=request.content,
                structured_representation=request.structured_payload,
                source=request.source,
                confidence=request.confidence,
                certainty=request.certainty,
                importance=request.importance,
                volatility=request.volatility,
                sensitivity=request.sensitivity,
                valid_from=request.valid_from or now,
                valid_until=request.valid_until,
                status=MemoryStatus.ACTIVE,
                created_at=now,
                observed_at=now,
                updated_at=now,
            )

            # 3. Provenance Attachment
            prov = self.provenance.create_provenance(
                memory_id=mem_id,
                source_type=request.source_type,
                source_identifier=request.source_identifier,
                actor=request.user_id,
            )
            entity.provenance = prov

            # 4. Grounding Evidence Attachment
            evi = self.evidence.attach_evidence(
                memory_id=mem_id,
                content=request.content,
                source=request.source,
                relation_type=EvidenceRelationType.SUPPORT,
                source_type=request.source_type,
                reliability=request.confidence,
                confidence=request.confidence,
                provenance_id=prov.provenance_id,
            )
            entity.supporting_evidence_ids.append(evi.evidence_id)

            # 5. Conflict Detection
            detected_conflicts = self.conflicts.detect_conflict(entity, existing_list)
            if detected_conflicts:
                entity.status = MemoryStatus.CONFLICTED
                entity.certainty = CertaintyState.CONTRADICTED
                for c in detected_conflicts:
                    self._emit_event("memory.conflicted", mem_id, {"conflict_id": c.conflict_id})

            # 6. Retention & Indexing
            self._memories[mem_id] = entity
            self.deduplication.register_memory(entity)
            self.vector_bridge.index_memory(entity)
            self.graph_bridge.sync_memory_node(entity, db=self.db)

            # 7. Attention Signals
            self.attention_bridge.notify_attention_engine(entity, detected_conflicts)

            self._emit_event(
                "memory.activated" if entity.status == MemoryStatus.ACTIVE else "memory.candidate_created",
                mem_id,
                {"type": entity.type.value, "status": entity.status.value},
            )

            return entity

    # --------------------------------------------------------------------------
    # Retrieval & Inspection
    # --------------------------------------------------------------------------

    def get_memory(self, memory_id: str) -> MemoryEntity | None:
        """Retrieve memory entity by ID."""
        return self._memories.get(memory_id)

    def list_memories(
        self,
        tenant_id: str = "default",
        status: MemoryStatus | None = None,
        type: MemoryType | None = None,
        include_stale: bool = False,
    ) -> list[MemoryEntity]:
        """List memories matching filter criteria."""
        results: list[MemoryEntity] = []
        for m in self._memories.values():
            if m.tenant_id != tenant_id:
                continue
            if status and m.status != status:
                continue
            if type and m.type != type:
                continue
            if not include_stale and m.status in (MemoryStatus.STALE, MemoryStatus.INVALIDATED, MemoryStatus.FORGOTTEN):
                continue
            results.append(m)
        return results

    # --------------------------------------------------------------------------
    # Phase 9 — Conflict Resolution
    # --------------------------------------------------------------------------

    def resolve_conflict(self, conflict_id: str, request: ConflictResolutionRequest) -> dict[str, Any]:
        """Attempt conflict resolution."""
        self._verify_mutation_allowed()

        with self._lock:
            conflict = self.conflicts.get_conflict(conflict_id)
            if not conflict:
                raise KeyError(f"Conflict '{conflict_id}' not found.")

            mem_a = self._memories.get(conflict.memory_a_id)
            mem_b = self._memories.get(conflict.memory_b_id)

            if not mem_a or not mem_b:
                raise KeyError("One or more conflicting memories are missing.")

            resolved, msg = self.resolution.resolve_conflict(
                conflict=conflict,
                memory_a=mem_a,
                memory_b=mem_b,
                evidence_manager=self.evidence,
                strategy=request.resolution_strategy,
                actor=request.resolved_by,
                override_winner_id=request.winning_memory_id,
            )

            if resolved:
                self._emit_event("memory.conflict_resolved", conflict.memory_a_id, {"conflict_id": conflict_id})

            return {"resolved": resolved, "message": msg, "conflict": conflict.model_dump()}

    # --------------------------------------------------------------------------
    # Phase 13 — Memory Consolidation
    # --------------------------------------------------------------------------

    def consolidate_explicit(
        self, episode_ids: list[str], summary: str, tenant_id: str = "default"
    ) -> dict[str, Any]:
        """Consolidate specified episodic memories into semantic knowledge."""
        self._verify_mutation_allowed()

        with self._lock:
            episodes = [self._memories[eid] for eid in episode_ids if eid in self._memories]
            if len(episodes) != len(episode_ids):
                raise KeyError("One or more episodic memory IDs not found.")

            sem_mem, rec = self.consolidation.consolidate_episodes(
                episodes=episodes,
                summary=summary,
                tenant_id=tenant_id,
                evidence_manager=self.evidence,
                provenance_tracker=self.provenance,
            )
            self._memories[sem_mem.memory_id] = sem_mem
            self.deduplication.register_memory(sem_mem)
            self.vector_bridge.index_memory(sem_mem)

            self._emit_event("memory.consolidated", sem_mem.memory_id, {"source_count": len(episodes)})

            return {
                "consolidated_memory": sem_mem.model_dump(),
                "consolidation_record": rec.model_dump(),
            }

    # --------------------------------------------------------------------------
    # Phase 20 — Context Assembly
    # --------------------------------------------------------------------------

    def assemble_context(self, query: str, tenant_id: str = "default", token_budget: int = 2000) -> dict[str, Any]:
        """Assemble bounded cognitive context surfacing any active contradictions."""
        with self._lock:
            active_mems = [m for m in self._memories.values() if m.tenant_id == tenant_id]
            active_conflicts = self.conflicts.list_active_conflicts()
            return self.context_assembler.assemble_context(
                query=query,
                memories=active_mems,
                active_conflicts=active_conflicts,
                token_budget=token_budget,
            )

    # --------------------------------------------------------------------------
    # Phase 21 — Forensic Reconstruction
    # --------------------------------------------------------------------------

    def reconstruct(self, request: MemoryReconstructionRequest) -> MemoryReconstructionResult:
        """Reconstruct chronological timeline and state without hallucination (safe read)."""
        with self._lock:
            mems = [m for m in self._memories.values() if m.tenant_id == request.tenant_id]
            conflicts = list(self.conflicts._conflicts.values())
            return self.reconstruction.reconstruct(
                request=request,
                memories=mems,
                conflicts=conflicts,
                evidence_manager=self.evidence,
            )

    # --------------------------------------------------------------------------
    # Phase 22 — Autonomous Revalidation
    # --------------------------------------------------------------------------

    def run_revalidation_scan(self, capability_changes: list[str] | None = None) -> list[dict[str, Any]]:
        """Scan and schedule revalidation jobs."""
        self._verify_mutation_allowed()

        with self._lock:
            jobs = self.revalidation.scan_revalidation_candidates(
                memories=list(self._memories.values()),
                temporal_engine=self.temporal,
                capability_changes=capability_changes,
            )
            for j in jobs:
                self._emit_event("memory.revalidated", j["memory_id"], {"job_id": j["job_id"]})
            return jobs

    # --------------------------------------------------------------------------
    # Lifecycle Transitions: Archive & Forget
    # --------------------------------------------------------------------------

    def archive_memory(self, memory_id: str, reason: str = "Archived by user or retention") -> MemoryEntity:
        """Transition memory to ARCHIVED."""
        self._verify_mutation_allowed()

        with self._lock:
            mem = self._memories.get(memory_id)
            if not mem:
                raise KeyError(f"Memory '{memory_id}' not found.")

            self.lifecycle.transition(mem, MemoryStatus.ARCHIVED, reason=reason)
            self._emit_event("memory.archived", memory_id, {"reason": reason})
            return mem

    def forget_memory(self, memory_id: str, reason: str = "Compliance or user forgetting", hard_delete: bool = False) -> MemoryEntity:
        """Transition memory to FORGOTTEN or delete."""
        self._verify_mutation_allowed()

        with self._lock:
            mem = self._memories.get(memory_id)
            if not mem:
                raise KeyError(f"Memory '{memory_id}' not found.")

            # Can transition to ARCHIVED then FORGOTTEN if needed
            if mem.status != MemoryStatus.ARCHIVED:
                self.lifecycle.transition(mem, MemoryStatus.ARCHIVED, reason="Pre-forget archive")

            self.lifecycle.transition(mem, MemoryStatus.FORGOTTEN, reason=reason)
            self.vector_bridge.index_memory(mem)  # Cleans up vector record

            self._emit_event("memory.forgotten", memory_id, {"hard_delete": hard_delete, "reason": reason})

            if hard_delete:
                del self._memories[memory_id]

            return mem

    # --------------------------------------------------------------------------
    # Health Telemetry
    # --------------------------------------------------------------------------

    def get_health(self, tenant_id: str = "default") -> dict[str, Any]:
        """Return operational and epistemological telemetry metrics."""
        with self._lock:
            mems = [m for m in self._memories.values() if m.tenant_id == tenant_id]
            total = len(mems)
            active = sum(1 for m in mems if m.status == MemoryStatus.ACTIVE)
            conflicted = sum(1 for m in mems if m.status == MemoryStatus.CONFLICTED)
            stale = sum(1 for m in mems if m.status == MemoryStatus.STALE)
            forgotten = sum(1 for m in mems if m.status == MemoryStatus.FORGOTTEN)
            hypotheses = sum(1 for m in mems if m.type == MemoryType.HYPOTHESIS)
            procedural = sum(1 for m in mems if m.type == MemoryType.PROCEDURAL)

            return {
                "tenant_id": tenant_id,
                "total_memories": total,
                "active_count": active,
                "conflicted_count": conflicted,
                "stale_count": stale,
                "forgotten_count": forgotten,
                "hypotheses_count": hypotheses,
                "procedural_count": procedural,
                "emergency_stop_active": self.emergency_stop.is_stopped(),
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Process-wide singleton
knowledge_consolidation_service = KnowledgeConsolidationService()


def get_knowledge_consolidation_service() -> KnowledgeConsolidationService:
    """Dependency provider for FastAPI routes."""
    return knowledge_consolidation_service
