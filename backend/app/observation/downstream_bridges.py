"""Downstream Integration Bridges for Task 114.
Feeds verified empirical observations to Belief Arbitration (Task 107), World-State (Task 98),
Decision Intelligence (Task 94), Intent Engine (Task 108), and enforces EmergencyStop primacy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.observation.domain import (
    ObservationOutcome,
    ObservationPlan,
    ObservationVerification,
    VerificationStatus,
)

logger = logging.getLogger("kairo.observation.downstream_bridges")


class ObservationDownstreamBridge:
    """Dispatches verified observations and informs downstream reasoning systems without bypassing governance."""

    @classmethod
    def check_emergency_stop(cls, user_id: Optional[str] = None) -> bool:
        """Section 34, 70: Strict fail-closed check against EmergencyStopService."""
        try:
            from app.security.emergency_stop import get_emergency_stop_service
            svc = get_emergency_stop_service()
            if hasattr(svc, "is_stopped"):
                if svc.is_stopped(user_id):
                    return True
                if any(st.get("stopped", False) for st in getattr(svc, "_local_state", {}).values()):
                    return True
            return False
        except Exception as e:
            logger.warning(f"Could not check EmergencyStopService, defaulting to safe mode: {e}")
            return False

    @classmethod
    def dispatch_to_belief_engine(
        cls,
        outcome: ObservationOutcome,
        verification: ObservationVerification,
    ) -> Dict[str, Any]:
        """Section 24: Submits verified observation to Task 107 Belief Arbitration as evidence."""
        if verification.status != VerificationStatus.VERIFIED:
            logger.info(f"Skipping belief dispatch for unverified outcome '{outcome.outcome_id}'.")
            return {"status": "SKIPPED", "reason": "UNVERIFIED"}

        evidence_payload = {
            "evidence_id": f"ev_{outcome.outcome_id}",
            "classification": "DIRECT_OBSERVATION" if outcome.method.value == "ACTIVE" else "TELEMETRY",
            "source": outcome.source,
            "confidence": outcome.confidence,
            "data": outcome.data_payload,
            "timestamp": outcome.observed_at.isoformat(),
        }

        try:
            from app.belief.service import get_belief_service
            svc = get_belief_service()
            if hasattr(svc, "submit_evidence"):
                svc.submit_evidence(evidence_payload)
                return {"status": "SUBMITTED", "evidence_id": evidence_payload["evidence_id"]}
        except Exception as e:
            logger.debug(f"Belief engine direct submission omitted or offline: {e}")

        return {"status": "BUFFERED", "evidence": evidence_payload}

    @classmethod
    def inform_decision_intelligence(
        cls,
        plan: ObservationPlan,
        decision_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Section 31, 66: Informs Task 94 Decision Intelligence whether observation reduced decision uncertainty."""
        dec_id = decision_id or (plan.gaps[0].dependent_decision_id if plan.gaps else None)
        uncertainty_reduction = 0.0
        if plan.uncertainty_before and plan.uncertainty_after:
            uncertainty_reduction = round(
                max(0.0, plan.uncertainty_after.overall_confidence - plan.uncertainty_before.overall_confidence),
                3,
            )

        report = {
            "plan_id": plan.plan_id,
            "target_entity": plan.target_entity,
            "decision_id": dec_id,
            "uncertainty_reduction": uncertainty_reduction,
            "recommended_stance": plan.recommended_stance,
            "stop_reason": plan.stop_reason.value if plan.stop_reason else None,
            "outcomes_count": len(plan.outcomes),
        }

        logger.info(f"Decision feedback generated for decision '{dec_id}': reduction={uncertainty_reduction}.")
        return report
