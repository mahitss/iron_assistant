"""Decision Memory and Safe Experience Consolidation Engine (Task 94 Phases 24 & 25).

Integrates with Task 92 Knowledge Consolidation.
Persists structured decision history, rationales, and verified outcomes without raw chain-of-thought.
Enforces decision reuse safeguards: marks drifted historical precedents as REFERENCE_ONLY.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.decision.domain import (
    DecisionOption,
    DecisionOutcomeRecord,
    DecisionV2Record,
)

logger = logging.getLogger("kairo.decision.memory")


class DecisionMemoryEngine:
    """Manages structured decision history, outcome feedback, and reuse safeguards."""

    def __init__(self) -> None:
        self._memory_store: dict[str, dict[str, Any]] = {}

    def record_precedent(self, decision: DecisionV2Record) -> dict[str, Any]:
        """Record a precedent directly into decision memory."""
        outcome = decision.outcomes[0] if decision.outcomes else None
        return self.consolidate_decision(decision, outcome=outcome)

    def find_precedents(
        self,
        query: str,
        decision_type: Any | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query historical decision precedents with safety classifications."""
        results = []
        q = query.lower()
        for record in self._memory_store.values():
            if decision_type:
                dt_val = decision_type.value if hasattr(decision_type, "value") else str(decision_type)
                if record.get("decision_type") != dt_val:
                    continue
            text = (
                f"{record.get('objective_id', '')} "
                f"{record.get('title', '')} "
                f"{record.get('selected_option', '')} "
                f"{record.get('decision_id', '')}"
            ).lower()
            q_tokens = [w for w in q.split() if w]
            if not q_tokens or all(tok in text for tok in q_tokens):
                res = dict(record)
                reuse_status, reason = self.evaluate_reuse_safety(record["decision_id"], {})
                res["reuse_status"] = "REFERENCE_ONLY" if reuse_status == "REFERENCE_ONLY" else "APPLICABLE_WITH_REVIEW"
                res["reuse_rationale"] = reason
                res["is_authoritative"] = False
                results.append(res)
        return results[:limit]

    def consolidate_decision(
        self,
        decision: DecisionV2Record,
        outcome: DecisionOutcomeRecord | None = None,
        lessons: list[str] | None = None,
    ) -> dict[str, Any]:
        """Consolidate a completed or evaluated decision into durable structured memory."""
        now = datetime.now(UTC)

        selected_name = decision.selected_option.name if decision.selected_option else "None"
        alternatives = [
            {"id": o.option_id, "name": o.name, "rejection_reason": o.rejection_reason}
            for o in decision.options
            if not decision.selected_option or o.option_id != decision.selected_option.option_id
        ]

        memory_record = {
            "decision_id": decision.decision_id,
            "objective_id": decision.objective_id,
            "title": getattr(decision, "title", ""),
            "decision_type": decision.decision_type.value,
            "status": decision.status.value,
            "selected_option": selected_name,
            "alternatives_considered": alternatives,
            "assumptions": [
                {"id": a.assumption_id, "statement": a.statement, "status": a.status.value}
                for a in decision.assumptions
            ],
            "risk_summary": decision.risk_summary,
            "resource_summary": decision.resource_summary,
            "certainty": decision.certainty.value,
            "predicted_outcomes": decision.expected_outcomes,
            "actual_outcomes": outcome.actual_outcome if outcome else decision.actual_outcomes,
            "outcome_deviation": outcome.deviation_score if outcome else 0.0,
            "verification_status": outcome.verification_status.value if outcome else decision.verification_status.value,
            "lessons_learned": lessons or (outcome.lessons_learned if outcome else []),
            "provenance": decision.provenance,
            "consolidated_at": now.isoformat(),
        }

        self._memory_store[decision.decision_id] = memory_record
        logger.info("Consolidated decision %s into decision memory", decision.decision_id)
        return memory_record

    def evaluate_reuse_safety(
        self,
        historical_decision_id: str,
        current_context: dict[str, Any],
        current_policy_version: str = "v1",
        current_capability_version: str = "v1",
    ) -> tuple[str, str]:
        """Verify environmental and policy alignment before using a historical decision.

        Returns: (REUSE_CLASS, RATIONALE)
        REUSE_CLASS in ['VALID_PREDECESSOR', 'REFERENCE_ONLY']
        """
        record = self._memory_store.get(historical_decision_id)
        if not record:
            return "REFERENCE_ONLY", "Historical decision not found in memory"

        provenance = record.get("provenance", {})
        historical_policy = provenance.get("policy_version", "v1")
        historical_cap_ver = provenance.get("capability_version", "v1")

        # Invariant: If policy, capability version, or critical assumptions changed -> REFERENCE_ONLY
        if historical_policy != current_policy_version:
            return "REFERENCE_ONLY", f"Policy version drifted ({historical_policy} -> {current_policy_version})"

        if historical_cap_ver != current_capability_version:
            return "REFERENCE_ONLY", f"Capability version drifted ({historical_cap_ver} -> {current_capability_version})"

        for asm in record.get("assumptions", []):
            if asm.get("status") == "INVALIDATED":
                return "REFERENCE_ONLY", f"Critical assumption '{asm.get('id')}' was invalidated"

        return "VALID_PREDECESSOR", "Context and policies remain congruent with historical execution"
