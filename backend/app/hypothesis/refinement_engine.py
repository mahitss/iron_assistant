"""Autonomous Hypothesis Refinement, Splitting, and Merging Engine (Task 115 Section 13, 37, 38).

Handles precision refinements:
- Splitting overly broad hypotheses into specialized sub-hypotheses with full parent-child lineage.
- Merging equivalent or duplicate hypotheses without deleting historical reasoning or evidence trails.
- Identifying semantic and causal relationships between competing explanations.

Hard Invariants:
- Splitting and merging ALWAYS preserve complete lineage and provenance.
- History is NEVER deleted.
- Equivalent hypotheses are linked with explicit relationship metadata.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.hypothesis.domain import (
    Hypothesis,
    HypothesisClaim,
    HypothesisConfidenceProfile,
    HypothesisFalsificationCondition,
    HypothesisRelationship,
    HypothesisRelationshipType,
    HypothesisSet,
    HypothesisStatus,
)

logger = logging.getLogger("kairo.hypothesis.refinement")


class RefinementEngine:
    """Manages splitting broad hypotheses and merging equivalent candidate explanations."""

    def split_hypothesis(
        self,
        hset: HypothesisSet,
        parent_hyp: Hypothesis,
        child_specs: List[Dict[str, Any]],
    ) -> List[Hypothesis]:
        """Splits a broad hypothesis into specialized, more granular child hypotheses."""
        if parent_hyp.status in (HypothesisStatus.SPLIT, HypothesisStatus.SUPERSEDED):
            logger.warning("Hypothesis %s has already been split or superseded.", parent_hyp.hypothesis_id)
            return []

        children: List[Hypothesis] = []
        child_ids: List[str] = []

        for spec in child_specs:
            child = Hypothesis(
                set_id=hset.set_id,
                statement=spec.get("statement", f"Specialized sub-hypothesis of {parent_hyp.hypothesis_id}"),
                claim=HypothesisClaim(
                    subject=spec.get("subject", parent_hyp.claim.subject),
                    predicate=spec.get("predicate", parent_hyp.claim.predicate),
                    object_value=spec.get("object_value", parent_hyp.claim.object_value),
                    target_metric=spec.get("target_metric", parent_hyp.claim.target_metric),
                    expected_direction=spec.get("expected_direction", parent_hyp.claim.expected_direction),
                ),
                scope=parent_hyp.scope,
                status=HypothesisStatus.UNDER_INVESTIGATION,
                provenance=parent_hyp.provenance,
                mechanism_summary=spec.get("mechanism_summary", parent_hyp.mechanism_summary),
                parent_hypothesis_ids=[parent_hyp.hypothesis_id],
                assumptions=list(parent_hyp.assumptions) + spec.get("assumptions", []),
                confidence_profile=HypothesisConfidenceProfile(
                    mechanism_plausibility=parent_hyp.confidence_profile.mechanism_plausibility,
                    uncertainty=0.65,
                ),
            )

            # Inherit falsification condition template if applicable
            for fc in parent_hyp.falsification_conditions:
                child.falsification_conditions.append(
                    HypothesisFalsificationCondition(
                        description=f"Child falsification: {fc.description}",
                        required_observations=fc.required_observations,
                        metric_thresholds=fc.metric_thresholds,
                        contradiction_signals=fc.contradiction_signals,
                    )
                )

            children.append(child)
            child_ids.append(child.hypothesis_id)

            # Add relationship: SPECIALIZES
            rel = HypothesisRelationship(
                source_hypothesis_id=child.hypothesis_id,
                target_hypothesis_id=parent_hyp.hypothesis_id,
                relationship_type=HypothesisRelationshipType.SPECIALIZES,
                rationale=f"Specialized variant of broad hypothesis {parent_hyp.hypothesis_id}",
            )
            hset.relationships.append(rel)

        # Update parent hypothesis
        parent_hyp.child_hypothesis_ids.extend(child_ids)
        parent_hyp.status = HypothesisStatus.SPLIT
        parent_hyp.updated_at = datetime.now(timezone.utc)

        # Update hypothesis set active IDs
        if parent_hyp.hypothesis_id in hset.active_hypothesis_ids:
            hset.active_hypothesis_ids.remove(parent_hyp.hypothesis_id)
        hset.active_hypothesis_ids.extend(child_ids)
        hset.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Split hypothesis %s into %d children: %s",
            parent_hyp.hypothesis_id,
            len(children),
            child_ids,
        )
        return children

    def merge_hypotheses(
        self,
        hset: HypothesisSet,
        source_hyps: List[Hypothesis],
        consolidated_statement: str,
    ) -> Hypothesis:
        """Merges two or more equivalent hypotheses into a single consolidated hypothesis while preserving lineage."""
        if len(source_hyps) < 2:
            raise ValueError("At least two hypotheses are required for merging.")

        source_ids = [h.hypothesis_id for h in source_hyps]
        primary = source_hyps[0]

        # Combine evidence references without duplication
        combined_supporting: List[str] = []
        combined_contradicting: List[str] = []
        combined_falsifying: List[str] = []
        combined_assumptions: List[str] = []

        for h in source_hyps:
            for s in h.supporting_evidence_ids:
                if s not in combined_supporting:
                    combined_supporting.append(s)
            for c in h.contradicting_evidence_ids:
                if c not in combined_contradicting:
                    combined_contradicting.append(c)
            for f in h.falsifying_evidence_ids:
                if f not in combined_falsifying:
                    combined_falsifying.append(f)
            for a in h.assumptions:
                if a not in combined_assumptions:
                    combined_assumptions.append(a)

        merged = Hypothesis(
            set_id=hset.set_id,
            statement=consolidated_statement,
            claim=primary.claim,
            scope=primary.scope,
            status=HypothesisStatus.UNDER_INVESTIGATION,
            provenance=primary.provenance,
            mechanism_summary=f"Consolidated explanation merged from {source_ids}: {primary.mechanism_summary}",
            parent_hypothesis_ids=source_ids,
            assumptions=combined_assumptions,
            supporting_evidence_ids=combined_supporting,
            contradicting_evidence_ids=combined_contradicting,
            falsifying_evidence_ids=combined_falsifying,
            falsification_conditions=list(primary.falsification_conditions),
            predictions=list(primary.predictions),
            confidence_profile=HypothesisConfidenceProfile(
                mechanism_plausibility=max(h.confidence_profile.mechanism_plausibility for h in source_hyps),
                evidence_strength=max(h.confidence_profile.evidence_strength for h in source_hyps),
                contradiction_score=max(h.confidence_profile.contradiction_score for h in source_hyps),
                uncertainty=min(h.confidence_profile.uncertainty for h in source_hyps),
            ),
        )

        # Mark source hypotheses as MERGED and link to merged ID
        now = datetime.now(timezone.utc)
        for h in source_hyps:
            h.status = HypothesisStatus.MERGED
            h.superseded_by_id = merged.hypothesis_id
            h.updated_at = now
            if h.hypothesis_id in hset.active_hypothesis_ids:
                hset.active_hypothesis_ids.remove(h.hypothesis_id)

            # Record relationship
            rel = HypothesisRelationship(
                source_hypothesis_id=h.hypothesis_id,
                target_hypothesis_id=merged.hypothesis_id,
                relationship_type=HypothesisRelationshipType.GENERALIZES,
                rationale=f"Merged into consolidated hypothesis {merged.hypothesis_id}",
            )
            hset.relationships.append(rel)

        hset.active_hypothesis_ids.append(merged.hypothesis_id)
        hset.updated_at = now

        logger.info(
            "Merged hypotheses %s into consolidated hypothesis %s",
            source_ids,
            merged.hypothesis_id,
        )
        return merged
