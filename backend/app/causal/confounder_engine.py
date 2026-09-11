"""Confounder, Mediator, and Collider Bias Analysis Engine (Task 73, Spec 11, 12, 13).

Strict Principles:
1. Confounders: Common causes create spurious correlation. When unadjusted, confidence must be penalized.
2. Mediators: Chains X -> M -> Y explain causal mechanisms rather than pure direct links.
3. Colliders: Conditioning on common effects X -> C <- Y creates spurious dependence.
"""

from __future__ import annotations

import logging
from typing import Any

from app.causal.discovery_schemas import (
    ColliderAnalysis,
    ConfounderAnalysis,
    ConfounderItem,
    MediatorAnalysis,
)

logger = logging.getLogger(__name__)


class ConfounderEngine:
    """Detects and adjusts for confounders, mediators, and collider structures in causal graphs."""

    @staticmethod
    def analyze_confounders(
        cause_entity: str,
        cause_var: str,
        effect_entity: str,
        effect_var: str,
        known_edges: list[dict[str, Any]],
        initial_confidence: float = 0.8,
    ) -> ConfounderAnalysis:
        """Scan known relationships to identify common causes Z -> X and Z -> Y."""
        cause_id = f"{cause_entity}:{cause_var}"
        effect_id = f"{effect_entity}:{effect_var}"

        # Build parents map: target -> set of parent nodes
        parents_of_cause: set[str] = set()
        parents_of_effect: set[str] = set()
        parent_evidence: dict[str, list[str]] = {}

        for edge in known_edges:
            src = f"{edge.get('cause_entity', '')}:{edge.get('cause_variable', '')}"
            tgt = f"{edge.get('effect_entity', '')}:{edge.get('effect_variable', '')}"
            ev = edge.get("evidence_refs", [])

            if tgt == cause_id:
                parents_of_cause.add(src)
                parent_evidence.setdefault(src, []).extend(ev)
            if tgt == effect_id:
                parents_of_effect.add(src)
                parent_evidence.setdefault(src, []).extend(ev)

        # Common causes: intersection of parents
        common_causes = list(parents_of_cause.intersection(parents_of_effect))
        candidate_items: list[ConfounderItem] = []

        for cc in common_causes:
            parts = cc.split(":", 1)
            e_name = parts[0]
            v_name = parts[1] if len(parts) > 1 else ""
            candidate_items.append(
                ConfounderItem(
                    variable=v_name,
                    entity=e_name,
                    relationship_to_cause="CAUSES",
                    relationship_to_effect="CAUSES",
                    evidence=parent_evidence.get(cc, []),
                    confidence=0.85,
                )
            )

        is_confounded = len(common_causes) > 0
        penalty = min(0.5, 0.25 * len(common_causes)) if is_confounded else 0.0
        adjusted_conf = max(0.1, round(initial_confidence - penalty, 2))

        rec = ""
        if is_confounded:
            cc_names = ", ".join(common_causes)
            rec = (
                f"Potential confounding detected via common cause(s): [{cc_names}]. "
                f"Controlled intervention DO({cause_id}) while holding [{cc_names}] constant is required."
            )

        return ConfounderAnalysis(
            candidate_confounders=candidate_items,
            common_causes=common_causes,
            is_confounded=is_confounded,
            confidence_penalty=penalty,
            adjusted_confidence=adjusted_conf,
            recommendation=rec,
        )

    @staticmethod
    def analyze_mediators(
        cause_entity: str,
        cause_var: str,
        effect_entity: str,
        effect_var: str,
        known_edges: list[dict[str, Any]],
    ) -> MediatorAnalysis:
        """Find mediating variables M such that X -> M and M -> Y."""
        cause_id = f"{cause_entity}:{cause_var}"
        effect_id = f"{effect_entity}:{effect_var}"

        # Children of cause (nodes X affects)
        children_of_cause: set[str] = set()
        # Parents of effect (nodes that affect Y)
        parents_of_effect: set[str] = set()

        for edge in known_edges:
            src = f"{edge.get('cause_entity', '')}:{edge.get('cause_variable', '')}"
            tgt = f"{edge.get('effect_entity', '')}:{edge.get('effect_variable', '')}"

            if src == cause_id and tgt != effect_id:
                children_of_cause.add(tgt)
            if tgt == effect_id and src != cause_id:
                parents_of_effect.add(src)

        # Mediators: intersection of children of cause and parents of effect
        mediator_nodes = list(children_of_cause.intersection(parents_of_effect))
        indirect_paths: list[list[str]] = []
        narratives: list[str] = []

        for m in mediator_nodes:
            path = [cause_id, m, effect_id]
            indirect_paths.append(path)
            narratives.append(f"{cause_id} -> {m} -> {effect_id}")

        is_mediated = len(mediator_nodes) > 0
        narrative = (
            f"Mediated mechanism detected: {', '.join(narratives)}"
            if is_mediated
            else "No mediating variables identified between cause and effect."
        )

        return MediatorAnalysis(
            mediator_variables=mediator_nodes,
            indirect_paths=indirect_paths,
            is_mediated=is_mediated,
            mechanism_narrative=narrative,
        )

    @staticmethod
    def detect_colliders(
        cause_a: str,
        cause_b: str,
        conditioned_on: str,
        known_edges: list[dict[str, Any]],
    ) -> ColliderAnalysis:
        """Evaluate whether conditioning on common effect C induces spurious collider association."""
        # Check if A -> C and B -> C
        parents_of_c: set[str] = set()
        for edge in known_edges:
            src = f"{edge.get('cause_entity', '')}:{edge.get('cause_variable', '')}"
            tgt = f"{edge.get('effect_entity', '')}:{edge.get('effect_variable', '')}"
            if tgt == conditioned_on:
                parents_of_c.add(src)

        is_collider = (cause_a in parents_of_c) and (cause_b in parents_of_c)
        warning = None
        if is_collider:
            warning = (
                f"Collider Conditioning Warning: Node '{conditioned_on}' is a common effect of both "
                f"'{cause_a}' and '{cause_b}'. Conditioning or filtering on '{conditioned_on}' may "
                f"induce a spurious association between '{cause_a}' and '{cause_b}'."
            )

        return ColliderAnalysis(
            collider_variable=conditioned_on if is_collider else None,
            cause_a=cause_a if is_collider else None,
            cause_b=cause_b if is_collider else None,
            is_conditioned=is_collider,
            warning=warning,
        )
