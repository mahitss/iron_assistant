"""Decision factor provenance and cryptographic fingerprinting for Task 57.

Tracks factor origin (objectives, constraints, risks, predictions, simulations,
causal basis, memory) and computes tamper-evident SHA-256 snapshots.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.decision.schemas import (
    CandidateOption,
    DecisionRanking,
    DecisionRequest,
    EvidenceSet,
    RiskAssessment,
)


class ProvenanceTracker:
    """Records factor origins and creates reproducible cryptographic snapshots."""

    def build_provenance_record(
        self,
        request: DecisionRequest,
        options: list[CandidateOption],
        ranking: DecisionRanking,
        evidence_set: EvidenceSet,
        risks: list[RiskAssessment],
        causal_context: dict[str, Any] | None = None,
        simulation_context: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        factor_sources = {
            "objectives": [
                {"id": o.objective_id, "name": o.name, "source": o.source, "weight": o.weight}
                for o in request.objectives
            ],
            "constraints": [
                {"id": c.constraint_id, "name": c.name, "type": c.constraint_type.value, "field": c.target_field}
                for c in request.constraints
            ],
            "evidence": [
                {"id": e.evidence_id, "source": e.source, "trust_level": e.trust_level.value, "strength": e.strength.value}
                for e in evidence_set.items
            ],
            "risks": [
                {"id": r.risk_id, "category": r.category.value, "exposure": r.exposure_score}
                for r in risks
            ],
            "causal_basis": causal_context.get("source", "causal_inference_engine") if causal_context else "none",
            "simulation_basis": simulation_context.get("source", "sandboxed_digital_twin") if simulation_context else "none",
            "historical_memory_basis": memory_context.get("source", "executive_memory") if memory_context else "none",
        }

        # Create canonical representation for fingerprinting
        canonical_payload = {
            "request_id": request.request_id,
            "question": request.question,
            "factor_sources": factor_sources,
            "recommended_option": ranking.recommended_option_id,
            "confidence": ranking.confidence,
        }

        serialized = json.dumps(canonical_payload, sort_keys=True, default=str)
        fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        return {
            "factor_sources": factor_sources,
            "fingerprint": fingerprint,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": request.authority,
            "kairo_subsystem": "kairo_executive_decision_engine",
            "version": 1,
        }


provenance_tracker = ProvenanceTracker()
