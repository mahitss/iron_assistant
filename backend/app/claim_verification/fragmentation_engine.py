"""Claim Fragmentation Engine for Task 116.
Decomposes complex, composite statements into structured atomic, causal,
temporal, quantitative, and relational claim fragments.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
import uuid

from app.claim_verification.domain import (
    Claim,
    ClaimFragment,
    ClaimType,
)


class ClaimFragmentationEngine:
    """Decomposes compound sentences and statements into structured claims and fragments."""

    # Causal conjunctions and indicators
    CAUSAL_MARKERS = [
        " because ", " due to ", " caused by ", " leading to ",
        " resulted in ", " as a result of ", " consequently ",
        " therefore ", " so that "
    ]

    # Temporal conjunctions and indicators
    TEMPORAL_MARKERS = [
        " after ", " before ", " while ", " during ",
        " subsequent to ", " prior to ", " since ", " until "
    ]

    # Conjunctions for composite claims
    COMPOSITE_MARKERS = [" and ", " as well as ", " furthermore ", " additionally "]

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Produce normalized lowercased whitespace-trimmed representation."""
        cleaned = re.sub(r"\s+", " ", text.strip().lower())
        # Strip trailing punctuation
        cleaned = re.sub(r"[\.,;:!?]+$", "", cleaned)
        return cleaned

    @classmethod
    def decompose_claim(
        cls,
        text: str,
        temporal_scope: Optional[Dict[str, Any]] = None,
        spatial_scope: Optional[Dict[str, Any]] = None,
        entity_scope: Optional[List[str]] = None,
        source_scope: Optional[Dict[str, Any]] = None,
        claim_id: Optional[str] = None,
    ) -> Claim:
        """Analyze text and decompose into structured Claim with atomic and relational fragments."""
        cid = claim_id or f"claim_{uuid.uuid4().hex[:12]}"
        normalized = cls.normalize_text(text)
        temporal_scope = temporal_scope or {}
        spatial_scope = spatial_scope or {}
        entity_scope = entity_scope or []
        source_scope = source_scope or {}

        # Detect claim type
        is_causal = any(marker in normalized for marker in cls.CAUSAL_MARKERS)
        is_temporal = any(marker in normalized for marker in cls.TEMPORAL_MARKERS)
        is_composite = any(marker in normalized for marker in cls.COMPOSITE_MARKERS)
        is_quantitative = bool(re.search(r"\b\d+(\.\d+)?(%|ms|s|m|gb|mb|kb|req/s|rps)?\b", normalized))

        if is_causal:
            claim_type = ClaimType.CAUSAL
        elif is_temporal:
            claim_type = ClaimType.TEMPORAL
        elif is_composite:
            claim_type = ClaimType.COMPOSITE
        elif is_quantitative:
            claim_type = ClaimType.QUANTITATIVE
        else:
            claim_type = ClaimType.ATOMIC

        fragments: List[ClaimFragment] = []

        if is_causal:
            fragments = cls._decompose_causal(cid, text, normalized)
        elif is_composite:
            fragments = cls._decompose_composite(cid, text, normalized)
        elif is_temporal:
            fragments = cls._decompose_temporal(cid, text, normalized)
        else:
            # Single atomic fragment
            subj, pred, obj = cls._extract_spo(normalized)
            fragments.append(
                ClaimFragment(
                    fragment_id=f"frag_{uuid.uuid4().hex[:8]}",
                    claim_id=cid,
                    fragment_type=claim_type,
                    statement=text.strip(),
                    subject=subj,
                    predicate=pred,
                    object_val=obj,
                    dependencies=[],
                    order_idx=0,
                )
            )

        # Primary SPO extraction for the top-level claim
        primary_subj, primary_pred, primary_obj = cls._extract_spo(normalized)

        # Falsification conditions
        falsification_conds = [
            f"Observed state contradicts '{primary_subj} {primary_pred}'",
            f"Evidence demonstrates opposite of '{primary_obj or text.strip()}'",
        ]

        expected_evidence_types = ["OBSERVATION", "METRIC", "LOG", "TELEMETRY", "DOCUMENT"]

        return Claim(
            claim_id=cid,
            version=1,
            canonical_text=text.strip(),
            normalized_text=normalized,
            claim_type=claim_type,
            subject=primary_subj,
            predicate=primary_pred,
            object_val=primary_obj,
            qualifiers={},
            temporal_scope=temporal_scope,
            spatial_scope=spatial_scope,
            entity_scope=entity_scope,
            source_scope=source_scope,
            conditions=[],
            assumptions=[],
            expected_evidence_types=expected_evidence_types,
            falsification_conditions=falsification_conds,
            verification_requirements=[
                f"Verify existence and state of {primary_subj or 'target entity'}",
                "Cross-check with independent telemetry or log artifacts",
            ],
            dependencies=[f.fragment_id for f in fragments[1:]] if len(fragments) > 1 else [],
            confidence=0.5,
            uncertainty=0.5,
            fragments=fragments,
        )

    @classmethod
    def _decompose_causal(cls, claim_id: str, original_text: str, normalized: str) -> List[ClaimFragment]:
        """Split causal statement into cause, effect, and causal relation fragments."""
        fragments: List[ClaimFragment] = []
        for marker in cls.CAUSAL_MARKERS:
            if marker in normalized:
                parts = normalized.split(marker, 1)
                effect_text = parts[0].strip()
                cause_text = parts[1].strip()

                eff_subj, eff_pred, eff_obj = cls._extract_spo(effect_text)
                frag_eff_id = f"frag_{uuid.uuid4().hex[:8]}"
                frag_eff = ClaimFragment(
                    fragment_id=frag_eff_id,
                    claim_id=claim_id,
                    fragment_type=ClaimType.ATOMIC,
                    statement=effect_text,
                    subject=eff_subj,
                    predicate=eff_pred,
                    object_val=eff_obj,
                    dependencies=[],
                    order_idx=0,
                )

                cause_subj, cause_pred, cause_obj = cls._extract_spo(cause_text)
                frag_cause_id = f"frag_{uuid.uuid4().hex[:8]}"
                frag_cause = ClaimFragment(
                    fragment_id=frag_cause_id,
                    claim_id=claim_id,
                    fragment_type=ClaimType.ATOMIC,
                    statement=cause_text,
                    subject=cause_subj,
                    predicate=cause_pred,
                    object_val=cause_obj,
                    dependencies=[],
                    order_idx=1,
                )

                # Causal linkage fragment
                frag_rel_id = f"frag_{uuid.uuid4().hex[:8]}"
                frag_rel = ClaimFragment(
                    fragment_id=frag_rel_id,
                    claim_id=claim_id,
                    fragment_type=ClaimType.CAUSAL,
                    statement=f"{cause_text} caused {effect_text}",
                    subject=cause_subj or cause_text,
                    predicate="CAUSES",
                    object_val=eff_subj or effect_text,
                    dependencies=[frag_cause_id, frag_eff_id],
                    order_idx=2,
                )

                fragments.extend([frag_eff, frag_cause, frag_rel])
                break

        if not fragments:
            # Fallback
            subj, pred, obj = cls._extract_spo(normalized)
            fragments.append(
                ClaimFragment(
                    fragment_id=f"frag_{uuid.uuid4().hex[:8]}",
                    claim_id=claim_id,
                    fragment_type=ClaimType.CAUSAL,
                    statement=original_text.strip(),
                    subject=subj,
                    predicate=pred,
                    object_val=obj,
                    dependencies=[],
                    order_idx=0,
                )
            )
        return fragments

    @classmethod
    def _decompose_composite(cls, claim_id: str, original_text: str, normalized: str) -> List[ClaimFragment]:
        """Decompose compound clauses joined by 'and', 'as well as', etc."""
        fragments: List[ClaimFragment] = []
        # Find first matching marker
        split_parts = [normalized]
        for marker in cls.COMPOSITE_MARKERS:
            if marker in normalized:
                split_parts = normalized.split(marker)
                break

        for idx, part in enumerate(split_parts):
            p_text = part.strip()
            if not p_text:
                continue
            subj, pred, obj = cls._extract_spo(p_text)
            fragments.append(
                ClaimFragment(
                    fragment_id=f"frag_{uuid.uuid4().hex[:8]}",
                    claim_id=claim_id,
                    fragment_type=ClaimType.ATOMIC,
                    statement=p_text,
                    subject=subj,
                    predicate=pred,
                    object_val=obj,
                    dependencies=[],
                    order_idx=idx,
                )
            )
        return fragments

    @classmethod
    def _decompose_temporal(cls, claim_id: str, original_text: str, normalized: str) -> List[ClaimFragment]:
        """Split temporally conditioned statement into ordered event fragments."""
        fragments: List[ClaimFragment] = []
        for marker in cls.TEMPORAL_MARKERS:
            if marker in normalized:
                parts = normalized.split(marker, 1)
                event_a = parts[0].strip()
                event_b = parts[1].strip()

                s_a, p_a, o_a = cls._extract_spo(event_a)
                frag_a_id = f"frag_{uuid.uuid4().hex[:8]}"
                frag_a = ClaimFragment(
                    fragment_id=frag_a_id,
                    claim_id=claim_id,
                    fragment_type=ClaimType.ATOMIC,
                    statement=event_a,
                    subject=s_a,
                    predicate=p_a,
                    object_val=o_a,
                    dependencies=[],
                    order_idx=0,
                )

                s_b, p_b, o_b = cls._extract_spo(event_b)
                frag_b_id = f"frag_{uuid.uuid4().hex[:8]}"
                frag_b = ClaimFragment(
                    fragment_id=frag_b_id,
                    claim_id=claim_id,
                    fragment_type=ClaimType.ATOMIC,
                    statement=event_b,
                    subject=s_b,
                    predicate=p_b,
                    object_val=o_b,
                    dependencies=[],
                    order_idx=1,
                )

                frag_rel_id = f"frag_{uuid.uuid4().hex[:8]}"
                frag_rel = ClaimFragment(
                    fragment_id=frag_rel_id,
                    claim_id=claim_id,
                    fragment_type=ClaimType.TEMPORAL,
                    statement=f"{event_a} {marker.strip()} {event_b}",
                    subject=s_a or event_a,
                    predicate=f"TEMPORAL_{marker.strip().upper()}",
                    object_val=s_b or event_b,
                    dependencies=[frag_a_id, frag_b_id],
                    order_idx=2,
                )
                fragments.extend([frag_a, frag_b, frag_rel])
                break

        if not fragments:
            subj, pred, obj = cls._extract_spo(normalized)
            fragments.append(
                ClaimFragment(
                    fragment_id=f"frag_{uuid.uuid4().hex[:8]}",
                    claim_id=claim_id,
                    fragment_type=ClaimType.TEMPORAL,
                    statement=original_text.strip(),
                    subject=subj,
                    predicate=pred,
                    object_val=obj,
                    dependencies=[],
                    order_idx=0,
                )
            )
        return fragments

    @classmethod
    def _extract_spo(cls, text: str) -> tuple[str, str, str]:
        """Simple deterministic Subject-Predicate-Object heuristic extractor."""
        words = text.split()
        if not words:
            return ("", "", "")
        if len(words) == 1:
            return (words[0], "EXISTS", "")
        if len(words) == 2:
            return (words[0], words[1], "")

        # Common auxiliary verbs
        verbs = ["is", "was", "are", "were", "became", "increased", "decreased", "occurred", "failed", "started", "stopped", "has", "had"]
        split_idx = -1
        for idx, w in enumerate(words):
            if w in verbs:
                split_idx = idx
                break

        if split_idx > 0:
            subj = " ".join(words[:split_idx])
            pred = words[split_idx]
            obj = " ".join(words[split_idx + 1:]) if split_idx + 1 < len(words) else ""
            return (subj, pred, obj)

        # Fallback: first word is subj, second is pred, rest is obj
        return (words[0], words[1], " ".join(words[2:]))
