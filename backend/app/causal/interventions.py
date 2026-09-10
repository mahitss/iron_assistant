"""Intervention modeling, safety gates, execution plans, and effect evaluation (Task 55)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.causal.evidence import create_evidence
from app.causal.safety import CausalSafetyGuard
from app.causal.schemas import (
    CausalEvidence,
    CausalHypothesis,
    EvidenceStrength,
    EvidenceType,
    HypothesisStatus,
    Intervention,
    InterventionType,
)


class InterventionEngine:
    """Manages causal interventions to test hypotheses safely without unauthorized production mutation."""

    @staticmethod
    def create_intervention(
        target: str,
        change: dict[str, Any],
        expected_effect: dict[str, Any],
        intervention_type: InterventionType = InterventionType.CONFIG_CHANGE,
        risk: str = "MEDIUM",
        verification_plan: list[str] | None = None,
        authorization: dict[str, Any] | None = None,
    ) -> Intervention:
        """Prompt #41, #42: Build an authorized intervention descriptor."""
        return Intervention(
            intervention_id=f"intv_{uuid.uuid4().hex[:12]}",
            target=target,
            change=change,
            intervention_type=intervention_type,
            expected_effect=expected_effect,
            authorization=authorization or {"approved": False, "role": "operator"},
            risk=risk,
            verification_plan=verification_plan or [
                "monitor_error_rate_5m",
                "check_latency_p99",
                "verify_upstream_health",
            ],
            status="PROPOSED",
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def validate_and_authorize(
        intervention: Intervention,
        is_production: bool = False,
        approved_by: str | None = None,
    ) -> Intervention:
        """Prompt #43, #44: Verify policy and authorization gates before execution."""
        is_approved = bool(intervention.authorization.get("approved")) or bool(approved_by)
        CausalSafetyGuard.validate_intervention_safety(
            target=intervention.target,
            risk=intervention.risk,
            is_production=is_production,
            is_approved=is_approved,
        )
        intervention.status = "AUTHORIZED"
        if approved_by:
            intervention.authorization["approved"] = True
            intervention.authorization["approved_by"] = approved_by
            intervention.authorization["approved_at"] = datetime.now(timezone.utc).isoformat()
        return intervention

    @staticmethod
    def evaluate_intervention_result(
        intervention: Intervention,
        actual_effect: dict[str, Any],
        hypothesis: CausalHypothesis | None = None,
    ) -> tuple[Intervention, CausalEvidence, bool]:
        """Prompt #46, #47, #48: Compare expected vs actual effect.

        Successful causal intervention increases evidence strength.
        Failure weakens only the tested hypothesis appropriately.
        """
        intervention.actual_effect = actual_effect
        intervention.status = "COMPLETED"

        # Compare expected effect keys with actual effect values
        effect_matched = True
        for k, v in intervention.expected_effect.items():
            actual_val = actual_effect.get(k)
            if actual_val is None or actual_val != v:
                # Check for numerical direction if provided (e.g. decreased, increased)
                if isinstance(v, str) and v.lower() == "decreased":
                    if not actual_effect.get(f"{k}_decreased", False):
                        effect_matched = False
                        break
                elif isinstance(v, str) and v.lower() == "increased":
                    if not actual_effect.get(f"{k}_increased", False):
                        effect_matched = False
                        break
                else:
                    effect_matched = False
                    break

        evidence_strength = EvidenceStrength.CRITICAL if effect_matched else EvidenceStrength.MODERATE
        evidence = create_evidence(
            evidence_type=EvidenceType.INTERVENTION,
            source=f"intervention:{intervention.intervention_id}",
            observation={
                "target": intervention.target,
                "change": intervention.change,
                "expected": intervention.expected_effect,
                "actual": actual_effect,
                "effect_matched": effect_matched,
            },
            strength=evidence_strength,
            independence=1.0,
        )

        if hypothesis:
            hypothesis.evidence.append(evidence)
            if effect_matched:
                hypothesis.confidence = min(0.99, hypothesis.confidence + 0.35)
                hypothesis.status = HypothesisStatus.SUPPORTED
            else:
                # Prompt #48: Failure weakens only the tested hypothesis appropriately
                hypothesis.confidence = max(0.05, hypothesis.confidence - 0.25)
                if hypothesis.confidence < 0.3:
                    hypothesis.status = HypothesisStatus.CONTRADICTED

        return intervention, evidence, effect_matched

    @staticmethod
    def check_safety_stop_condition(
        current_metrics: dict[str, float],
        safety_thresholds: dict[str, float] | None = None,
    ) -> tuple[bool, str | None]:
        """Prompt #192, #193: Stop intervention if safety threshold is crossed."""
        thresholds = safety_thresholds or {
            "error_rate": 0.05,  # 5% max error rate
            "latency_p99_ms": 2000.0,
            "cpu_saturation": 0.95,
        }
        for metric, threshold in thresholds.items():
            val = current_metrics.get(metric)
            if val is not None and val > threshold:
                return True, f"Safety threshold crossed for metric '{metric}': {val} > {threshold}"
        return False, None

    @staticmethod
    def rollback_intervention(
        intervention: Intervention,
        rollback_command: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prompt #194: Execute safe, verified rollback for an intervention."""
        intervention.status = "ROLLED_BACK"
        return {
            "intervention_id": intervention.intervention_id,
            "target": intervention.target,
            "status": "ROLLED_BACK",
            "rollback_plan": rollback_command or {"action": "revert_change", "original": intervention.change},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
