"""Controlled causal experiments, A/B comparisons, safety guards, and contamination checks (Task 55)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.causal.safety import CausalSafetyGuard
from app.causal.schemas import CausalExperiment


class CausalExperimentEngine:
    """Manages controlled causal A/B experiments with authorization, contamination checks, and safety stop conditions."""

    @staticmethod
    def create_experiment(
        hypothesis_id: str,
        treatment: dict[str, Any],
        control: dict[str, Any],
        metric: str,
        duration_seconds: int = 300,
        authorization: dict[str, Any] | None = None,
        is_high_risk: bool = False,
    ) -> CausalExperiment:
        """Prompt #74, #75, #76: Create a controlled experiment draft."""
        auth = authorization or {"approved": False, "role": "operator"}
        # If high risk and not approved, block execution attempt
        if is_high_risk and not auth.get("approved"):
            CausalSafetyGuard.validate_experiment_safety(
                hypothesis_id=hypothesis_id,
                is_high_risk=is_high_risk,
                is_approved=False,
            )

        return CausalExperiment(
            experiment_id=f"exp_{uuid.uuid4().hex[:12]}",
            hypothesis_id=hypothesis_id,
            treatment=treatment,
            control=control,
            metric=metric,
            duration_seconds=duration_seconds,
            authorization=auth,
            status="PENDING_APPROVAL" if not auth.get("approved") else "APPROVED",
            result=None,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def authorize_experiment(
        experiment: CausalExperiment,
        approved_by: str,
        approver_role: str = "sre_lead",
    ) -> CausalExperiment:
        """Prompt #75: Formally approve a causal experiment."""
        experiment.authorization["approved"] = True
        experiment.authorization["approved_by"] = approved_by
        experiment.authorization["approver_role"] = approver_role
        experiment.authorization["approved_at"] = datetime.now(timezone.utc).isoformat()
        experiment.status = "APPROVED"
        return experiment

    @staticmethod
    def check_contamination_risk(
        treatment: dict[str, Any],
        control: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Prompt #77: Detect shared dependencies that could cause treatment/control contamination."""
        warnings: list[str] = []
        set(treatment.keys()).intersection(set(control.keys()))

        # Check if both groups share identical instance IDs or stateful shared caches
        if treatment.get("cache_host") and treatment.get("cache_host") == control.get("cache_host"):
            warnings.append("Shared cache host detected between treatment and control.")
        if treatment.get("db_cluster") and treatment.get("db_cluster") == control.get("db_cluster"):
            warnings.append("Shared database cluster detected between treatment and control.")

        has_contamination = len(warnings) > 0
        return has_contamination, warnings

    @staticmethod
    def evaluate_experiment_results(
        experiment: CausalExperiment,
        treatment_val: float,
        control_val: float,
        safety_stop_triggered: bool = False,
    ) -> dict[str, Any]:
        """Prompt #78, #80, #195: Track predefined outcomes and record audit details."""
        if safety_stop_triggered:
            experiment.status = "ABORTED_SAFETY_STOP"
            experiment.result = {
                "aborted": True,
                "reason": "Safety stop condition triggered during experiment.",
                "treatment_metric": treatment_val,
                "control_metric": control_val,
            }
            return experiment.result

        delta = treatment_val - control_val
        delta_pct = (delta / control_val * 100.0) if control_val != 0 else 0.0

        # Outcome deemed significant if delta is measurable (> 5% shift)
        is_significant = abs(delta_pct) >= 5.0
        supports_hypothesis = delta < 0 if "latency" in experiment.metric or "error" in experiment.metric else delta > 0

        res = {
            "metric": experiment.metric,
            "treatment_value": treatment_val,
            "control_value": control_val,
            "delta": round(delta, 4),
            "delta_pct": round(delta_pct, 2),
            "is_significant": is_significant,
            "supports_hypothesis": supports_hypothesis,
            "aborted": False,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }

        experiment.result = res
        experiment.status = "COMPLETED"
        return res
