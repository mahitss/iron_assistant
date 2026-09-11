"""Provenance and self-reinforcement defense engine for Task 68.

Enforces:
- Spec 7: Memory lineage preservation (SOURCE -> OBSERVATION -> EVENT -> MEMORY -> CLAIM -> DECISION -> ACTION -> OUTCOME)
- Spec 19: Self-reinforcement defense (prevents circular confirmation where derived summaries pose as independent empirical evidence)
"""

from __future__ import annotations

import logging
from typing import Any

from app.memory_consolidation.schemas import MemoryProvenance

logger = logging.getLogger("kairo.memory_consolidation.provenance")


class ProvenanceTracker:
    """Manages memory derivation DAGs and guards against circular self-confirmation."""

    @classmethod
    def derive_memory_provenance(
        cls,
        parent_provenances: list[MemoryProvenance],
        derived_memory_id: str,
        source_memory_ids: list[str] | None = None,
        actor: str = "consolidation_worker",
    ) -> MemoryProvenance:
        """Create a derived provenance object that strictly preserves ancestor lineage (Spec 7, 19)."""
        all_source_refs: set[str] = set()
        all_parent_ids: set[str] = set()
        all_derived_ids: set[str] = set(source_memory_ids or [])
        all_decisions: set[str] = set()
        all_goals: set[str] = set()
        all_evidence: set[str] = set()
        combined_generation_lineage: list[str] = []

        for p in parent_provenances:
            all_source_refs.update(p.source_refs)
            if p.source_id:
                all_source_refs.add(p.source_id)
            all_parent_ids.update(p.parent_memory_ids)
            all_derived_ids.update(p.derived_from_ids)
            all_decisions.update(p.decision_refs)
            all_goals.update(p.goal_refs)
            all_evidence.update(p.evidence_refs)
            combined_generation_lineage.extend(p.generation_lineage)

        # INVARIANT 19: Derived memories are NOT independent sources
        is_independent = False
        combined_generation_lineage.append(f"derived:{derived_memory_id}")

        return MemoryProvenance(
            source_type="derived_consolidation",
            source_refs=sorted(all_source_refs),
            parent_memory_ids=sorted(all_parent_ids),
            derived_from_ids=sorted(
                [p.source_id for p in parent_provenances if p.source_id] + list(all_derived_ids)
            ),
            decision_refs=sorted(all_decisions),
            goal_refs=sorted(all_goals),
            evidence_refs=sorted(all_evidence),
            generation_lineage=combined_generation_lineage,
            is_independent_source=is_independent,
            actor=actor,
        )

    @classmethod
    def check_source_independence(
        cls, prov_a: MemoryProvenance, prov_b: MemoryProvenance
    ) -> tuple[bool, str]:
        """Verify whether two memories originate from genuinely independent sources (Spec 8, 19).

        Repetition of a claim across multiple agents does not equal independent confirmation.
        """
        # If either was derived from the other
        if prov_a.source_id in prov_b.derived_from_ids or prov_b.source_id in prov_a.derived_from_ids:
            return False, "CIRCULAR_DERIVATION: One memory was derived from the other."

        # If they share the exact same raw source references
        shared_sources = set(prov_a.source_refs) & set(prov_b.source_refs)
        if shared_sources:
            return False, f"SHARED_PRIMARY_SOURCE: Both rely on primary sources {sorted(shared_sources)}."

        # If both are agent-generated summaries with overlapping lineage
        shared_gen = set(prov_a.generation_lineage) & set(prov_b.generation_lineage)
        if shared_gen:
            return False, f"SHARED_GENERATION_LINEAGE: Overlapping generation steps {sorted(shared_gen)}."

        return True, "INDEPENDENT_SOURCES: No shared primary sources or derivation lineage detected."

    @classmethod
    def build_provenance_summary(cls, prov: MemoryProvenance) -> dict[str, Any]:
        """Serialize complete explainable lineage graph for APIs (Spec 7)."""
        return {
            "source_type": prov.source_type,
            "source_id": prov.source_id,
            "source_refs": prov.source_refs,
            "parent_memory_ids": prov.parent_memory_ids,
            "derived_from_ids": prov.derived_from_ids,
            "is_independent_source": prov.is_independent_source,
            "generation_depth": len(prov.generation_lineage),
            "generation_lineage": prov.generation_lineage,
            "goal_dependencies": prov.goal_refs,
            "decision_dependencies": prov.decision_refs,
            "evidence_count": len(prov.evidence_refs),
        }
