"""Multi-agent coordination, synchronization barriers, structured handoffs, and consensus (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.safety import (
    OrchestrationSafetyError,
    verify_separation_of_duties,
)

logger = logging.getLogger(__name__)


class CoordinationEngine:
    """Coordinates multi-agent interactions, synchronization barriers, handoff validation, and disagreement resolution."""

    def validate_handoff(
        self,
        source_agent: str,
        target_agent: str,
        payload: dict[str, Any],
        expected_schema: dict[str, Any] | None = None,
        is_high_impact: bool = False,
    ) -> dict[str, Any]:
        """Validate an explicit data handoff between two agents."""
        if not payload:
            raise OrchestrationSafetyError(f"Handoff from '{source_agent}' to '{target_agent}' failed: empty payload.")

        # If high impact, ensure separation of duties
        if is_high_impact:
            verify_separation_of_duties(
                creator=source_agent,
                reviewer=target_agent,
                is_high_impact=True,
            )

        # Basic schema key validation if expected_schema provided
        if expected_schema and "required" in expected_schema:
            for required_field in expected_schema["required"]:
                if required_field not in payload:
                    raise OrchestrationSafetyError(
                        f"Handoff validation error: Missing required field '{required_field}' in output from '{source_agent}'."
                    )

        logger.info(
            "HANDOFF_VALIDATED: from=%s to=%s payload_keys=%s",
            source_agent,
            target_agent,
            list(payload.keys()),
        )
        return {
            "status": "VALIDATED",
            "source_agent": source_agent,
            "target_agent": target_agent,
            "data": payload,
        }

    def check_synchronization_barrier(
        self,
        barrier_id: str,
        converging_tasks: list[str],
        completed_tasks: set[str],
    ) -> bool:
        """Evaluate if all tasks feeding a synchronization barrier have completed."""
        missing = [t for t in converging_tasks if t not in completed_tasks]
        if missing:
            logger.info("BARRIER_WAITING: barrier=%s waiting_on=%s", barrier_id, missing)
            return False

        logger.info("BARRIER_SATISFIED: barrier=%s all tasks completed", barrier_id)
        return True

    def resolve_agent_disagreement(
        self,
        agent_opinions: list[dict[str, Any]],
        resolution_strategy: str = "WEIGHTED_SPECIALIST",
    ) -> dict[str, Any]:
        """Resolve conflicting agent evaluations without fabricating false consensus.

        Preserves individual agent outputs and rationales.
        """
        if not agent_opinions:
            raise OrchestrationSafetyError("No agent opinions provided for disagreement resolution.")

        if len(agent_opinions) == 1:
            return {
                "resolved": True,
                "winner": agent_opinions[0],
                "all_opinions": agent_opinions,
                "rationale": "Single opinion provided.",
            }

        # Check if unanimous
        distinct_conclusions = {op.get("conclusion") for op in agent_opinions}
        if len(distinct_conclusions) == 1:
            return {
                "resolved": True,
                "winner": agent_opinions[0],
                "all_opinions": agent_opinions,
                "rationale": "Unanimous agreement.",
            }

        # Weighted specialist agreement: weight by specialist role / confidence
        scored_opinions = []
        for op in agent_opinions:
            conf = float(op.get("confidence", 0.5))
            is_specialist = bool(op.get("is_specialist", False))
            weight = conf * (1.5 if is_specialist else 1.0)
            scored_opinions.append((weight, op))

        scored_opinions.sort(key=lambda x: x[0], reverse=True)
        top_weight, top_op = scored_opinions[0]

        return {
            "resolved": True,
            "winner": top_op,
            "winner_weight": round(top_weight, 3),
            "all_opinions": agent_opinions,
            "rationale": f"Resolved using {resolution_strategy} based on specialist weighting and confidence.",
        }


coordination_engine = CoordinationEngine()
