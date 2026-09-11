"""Ingestion, normalization, and classification capture pipeline for Task 68.

Enforces:
- Spec 2: Strict cognitive distinctions (simulation != experience, prediction != event, memory != truth)
- Spec 6: Multi-source capture normalization and trust assessment
- Spec 17: Memory poisoning prevention
- Spec 29: Secret and credential scrubbing
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.memory_consolidation.safety import MemorySafetyGuard
from app.memory_consolidation.schemas import (
    CognitiveClassification,
    DurableMemory,
    FreshnessState,
    MemoryCaptureRequest,
    MemoryLifecycleState,
    MemoryProvenance,
    MemoryType,
    TrustLevel,
)

logger = logging.getLogger("kairo.memory_consolidation.capture")


class MemoryCapturePipeline:
    """Pipelines incoming raw experiences, observations, and claims into structured memories."""

    @classmethod
    def process_capture(
        cls, request: MemoryCaptureRequest
    ) -> tuple[DurableMemory, MemoryProvenance, list[dict[str, any]]]:
        """Execute complete normalization, safety inspection, and cognitive classification."""
        # 1. Scrub secrets and credentials
        clean_content = MemorySafetyGuard.scrub_secrets(request.content)
        clean_payload = MemorySafetyGuard.sanitize_payload(request.structured_payload)

        # 2. Assess trust and check for memory poisoning attempts
        assessed_trust, flags = MemorySafetyGuard.assess_trust_and_poisoning(
            clean_content, source_type=request.source_type
        )
        if request.trust_level == TrustLevel.QUARANTINED or assessed_trust == TrustLevel.QUARANTINED:
            initial_status = MemoryLifecycleState.QUARANTINED
            final_trust = TrustLevel.QUARANTINED
        else:
            initial_status = MemoryLifecycleState.ACTIVE
            final_trust = (
                assessed_trust if request.trust_level == TrustLevel.UNVERIFIED else request.trust_level
            )

        # 3. Enforce Cognitive Invariants (Spec 2)
        cog_type = request.cognitive_type
        mem_type = request.memory_type

        # Invariant: Simulation is not real experience
        if cog_type == CognitiveClassification.SIMULATION and mem_type == MemoryType.EPISODIC_MEMORY:
            logger.info(
                "Cognitive correction: simulations cannot be stored as EPISODIC_MEMORY; mapping to WORKING_MEMORY."
            )
            mem_type = MemoryType.WORKING_MEMORY

        # Invariant: Prediction is not an observed event or outcome
        if cog_type == CognitiveClassification.PREDICTION and mem_type == MemoryType.EPISODIC_MEMORY:
            logger.info(
                "Cognitive correction: predictions cannot be stored as EPISODIC_MEMORY; mapping to PROSPECTIVE_MEMORY."
            )
            mem_type = MemoryType.PROSPECTIVE_MEMORY

        # Invariant: External summaries do not count as verified facts
        if cog_type in {CognitiveClassification.SUMMARY, CognitiveClassification.DERIVED_KNOWLEDGE}:
            if final_trust == TrustLevel.VERIFIED:
                final_trust = TrustLevel.UNVERIFIED

        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)

        # 4. Construct Provenance
        provenance = MemoryProvenance(
            provenance_id=f"prv_{uuid.uuid4().hex[:10]}",
            source_type=request.source_type,
            source_id=request.source_id,
            source_refs=list(request.source_refs),
            parent_memory_ids=list(request.parent_memory_ids),
            derived_from_ids=[],
            goal_refs=list(request.goal_refs),
            decision_refs=list(request.decision_refs),
            plan_refs=list(request.plan_refs),
            generation_lineage=[f"capture:{request.source_type}"],
            is_independent_source=True,
            actor="kairo_capture_pipeline",
        )

        # 5. Construct DurableMemory
        memory = DurableMemory(
            memory_id=memory_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            project_id=request.project_id,
            cognitive_type=cog_type,
            memory_type=mem_type,
            content=clean_content,
            structured_payload=clean_payload,
            confidence=request.confidence,
            importance=request.importance,
            relevance=1.0,
            freshness=FreshnessState.FRESH,
            sensitivity=request.sensitivity,
            trust_level=final_trust,
            created_at=now,
            observed_at=now,
            valid_from=request.valid_from or now,
            valid_until=request.valid_until,
            expires_at=request.expires_at,
            last_accessed_at=now,
            status=initial_status,
            version=1,
            provenance=provenance,
            created_by="capture_pipeline",
            updated_by="capture_pipeline",
        )

        audit_events: list[dict[str, any]] = [
            {
                "audit_id": f"maud_{uuid.uuid4().hex[:10]}",
                "memory_id": memory_id,
                "tenant_id": request.tenant_id,
                "event_type": "MEMORY_CAPTURED",
                "actor": "capture_pipeline",
                "previous_state": None,
                "new_state": initial_status.value,
                "reason": f"Captured from {request.source_type}",
                "details": {"flags": flags, "cognitive_type": cog_type.value},
                "timestamp": now,
            }
        ]

        if initial_status == MemoryLifecycleState.QUARANTINED:
            audit_events.append(
                {
                    "audit_id": f"maud_{uuid.uuid4().hex[:10]}",
                    "memory_id": memory_id,
                    "tenant_id": request.tenant_id,
                    "event_type": "MEMORY_QUARANTINED",
                    "actor": "safety_guard",
                    "previous_state": MemoryLifecycleState.CAPTURED.value,
                    "new_state": MemoryLifecycleState.QUARANTINED.value,
                    "reason": f"Quarantined due to poisoning flags: {flags}",
                    "details": {"flags": flags},
                    "timestamp": now,
                }
            )

        return memory, provenance, audit_events
