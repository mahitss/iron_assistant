"""Cross-subsystem integration hooks for Task 68.

Enforces:
- Spec 24: Deep integration with Tasks 42, 44, 47, 50, 52, 53, 57, 61, 64, 65, 66, 67
- Spec 38: Metacognitive Self-Audit integration detecting unsupported beliefs, stale information, and poisoning
"""

from __future__ import annotations

import logging
from typing import Any

from app.memory_consolidation.schemas import (
    CognitiveClassification,
    DurableMemory,
    FreshnessState,
    MemoryLifecycleState,
    MemoryType,
    TrustLevel,
)

logger = logging.getLogger("kairo.memory_consolidation.integrator")


class MemorySubsystemIntegrator:
    """Orchestrates bidirectional data flow between memory consolidation and other Kairo subsystems."""

    @classmethod
    def apply_verification_outcome(
        cls, memory: DurableMemory, verification_passed: bool, evidence_ref: str
    ) -> None:
        """Integrate Task 42 Truth & Verification outcome."""
        if verification_passed:
            memory.trust_level = TrustLevel.VERIFIED
            memory.cognitive_type = CognitiveClassification.VERIFIED_FACT
            memory.confidence = min(memory.confidence + 0.1, 1.0)
            memory.provenance.verification_refs.append(evidence_ref)
        else:
            memory.trust_level = TrustLevel.UNVERIFIED
            memory.confidence = max(memory.confidence - 0.2, 0.1)

    @classmethod
    def promote_to_executive(cls, memory: DurableMemory, reason: str) -> None:
        """Integrate with Task 53 Executive Memory."""
        memory.memory_type = MemoryType.EXECUTIVE_MEMORY
        memory.status = MemoryLifecycleState.PROMOTED
        memory.importance = max(memory.importance, 0.9)
        memory.provenance.generation_lineage.append(f"promoted_to_executive:{reason}")

    @classmethod
    def audit_memory_subsystem_quality(cls, memories: list[DurableMemory]) -> list[dict[str, Any]]:
        """Integrate with Task 67 Metacognitive Self-Audit Engine (Spec 38)."""
        findings: list[dict[str, Any]] = []

        for m in memories:
            # 1. Check for stale memory masquerading as active
            if m.freshness == FreshnessState.STALE and m.status == MemoryLifecycleState.ACTIVE:
                findings.append(
                    {
                        "category": "STALE_MEMORY_RISK",
                        "severity": "MEDIUM",
                        "memory_id": m.memory_id,
                        "description": f"Memory {m.memory_id} is stale but remains in ACTIVE lifecycle state.",
                    }
                )

            # 2. Check for unverified summaries claiming fact status
            if (
                m.cognitive_type == CognitiveClassification.VERIFIED_FACT
                and m.provenance.source_type == "derived_consolidation"
                and not m.provenance.verification_refs
            ):
                findings.append(
                    {
                        "category": "UNVERIFIED_DERIVED_FACT",
                        "severity": "HIGH",
                        "memory_id": m.memory_id,
                        "description": "Derived summary falsely categorized as VERIFIED_FACT without external verification.",
                    }
                )

            # 3. Check for missing provenance
            if not m.provenance.source_refs and not m.provenance.parent_memory_ids:
                findings.append(
                    {
                        "category": "MISSING_PROVENANCE",
                        "severity": "LOW",
                        "memory_id": m.memory_id,
                        "description": f"Memory {m.memory_id} has no source references or parent memories.",
                    }
                )

            # 4. Check for quarantined poisoning attempts
            if m.status == MemoryLifecycleState.QUARANTINED and m.trust_level == TrustLevel.QUARANTINED:
                findings.append(
                    {
                        "category": "QUARANTINED_POISONING_ATTEMPT",
                        "severity": "HIGH",
                        "memory_id": m.memory_id,
                        "description": "Detected adversarial prompt injection or memory poisoning attempt in quarantine.",
                    }
                )

        return findings
