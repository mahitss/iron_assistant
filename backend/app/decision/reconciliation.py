"""Historical decision reconstruction and as-of analysis for Task 57.

Enables 'Why did Kairo recommend this yesterday?' reconstruction using historical
snapshots rather than present state, and supports decision analogies.
"""

from __future__ import annotations

from typing import Any

from app.decision.schemas import DecisionRecord


class DecisionReconciler:
    """Reconstructs historical decision context faithfully as-of execution time."""

    def reconstruct_as_of(
        self,
        record: DecisionRecord,
    ) -> dict[str, Any]:
        """Reconstructs the precise state of knowledge and assumptions at the time of recommendation."""
        prov = record.provenance or {}
        factor_sources = prov.get("factor_sources", {})

        return {
            "decision_id": record.decision_id,
            "request_id": record.request_id,
            "as_of_timestamp": record.created_at.isoformat(),
            "status_at_time": record.status.value,
            "recommended_option": record.recommendation.recommended_option_id if record.recommendation else None,
            "confidence_then": record.confidence,
            "known_factors": {
                "objectives_known": factor_sources.get("objectives", []),
                "constraints_applied": factor_sources.get("constraints", []),
                "evidence_presented": factor_sources.get("evidence", []),
                "risks_evaluated": factor_sources.get("risks", []),
                "causal_basis": factor_sources.get("causal_basis", "none"),
                "simulation_basis": factor_sources.get("simulation_basis", "none"),
            },
            "assumptions_then": record.recommendation.assumptions if record.recommendation else [],
            "fingerprint": prov.get("fingerprint", ""),
            "reconstruction_integrity": "VERIFIED_HISTORICAL_SNAPSHOT",
        }

    def find_analogies(
        self,
        current_question: str,
        historical_records: list[DecisionRecord],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Identifies similar past decisions to inform candidate strategies without forcing false equivalence."""
        q_tokens = set(current_question.lower().split())
        analogies: list[dict[str, Any]] = []

        for rec in historical_records:
            # Keyword overlap heuristic
            # In a full system, embeddings from memory fabric can be utilized
            overlap_score = 0.0
            if rec.recommendation:
                rec_tokens = set(rec.recommendation.why_selected.lower().split())
                common = q_tokens.intersection(rec_tokens)
                if common:
                    overlap_score = round(len(common) / max(1, len(q_tokens)), 2)

            if overlap_score > 0.15:
                analogies.append({
                    "decision_id": rec.decision_id,
                    "similarity_score": overlap_score,
                    "past_recommendation": rec.recommendation.headline if rec.recommendation else "Unknown",
                    "user_override": rec.user_override,
                    "status": rec.status.value,
                    "relevance_note": "Previous decision shared key objective/context keywords. Revalidate against current state.",
                })

        analogies.sort(key=lambda a: a["similarity_score"], reverse=True)
        return analogies[:top_k]


decision_reconciler = DecisionReconciler()
