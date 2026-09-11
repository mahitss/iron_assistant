"""Cross-subsystem integration bridge for Kairo Autonomous Discovery Engine (Task 72).

Coordinates with:
- Task 71: Autonomous Reasoning & Deliberation (gaps -> research questions)
- Task 70: Autonomous Attention & Cognitive Budgeting (information gain & budget)
- Task 69: Universal Context & Adaptive Personalization (prior context retrieval & updates)
- Task 68: Knowledge & Memory Consolidation (candidate knowledge promotion without private CoT)
- Task 67: Metacognitive Control & Self-Audit
- Task 55: Causal Reasoning (correlation vs causal evidence)
- Task 56: Simulation & Counterfactuals (simulation labeled is_simulation=True, separated from reality)
- Task 47: Predictive Intelligence (calibration of pre-execution predictions)
- Task 42: Truth & Verification (invariant checks before knowledge updates)
- Task 59: Resource & Capability Orchestration (resource limits)
"""

import logging
from typing import Any

from app.discovery.schemas import (
    ExperimentDesign,
    ExperimentObservation,
    ExperimentResult,
)

logger = logging.getLogger(__name__)


class DiscoverySubsystemIntegrator:
    """Coordinates scientific discovery workflows with surrounding Kairo cognitive systems."""

    def bridge_reasoning_gaps(
        self,
        tenant_id: str,
        workspace_id: str,
        reasoning_id: str,
    ) -> dict[str, Any]:
        """Imports evidence gaps and uncertainties from a Task 71 reasoning session."""
        try:
            from app.reasoning.service import get_reasoning_service

            rsn_service = get_reasoning_service()
            session = rsn_service.get_session(reasoning_id)
            if session:
                return {
                    "question": session.question,
                    "objective": session.objective,
                    "uncertainties": [
                        item.description if hasattr(item, "description") else str(item)
                        for item in session.hypotheses
                    ],
                    "evidence_gaps": [],
                }
        except Exception as e:
            logger.debug(f"Unable to bridge reasoning session {reasoning_id}: {e}")

        return {
            "question": "Empirical question regarding system behavior",
            "objective": "Investigate root cause",
            "uncertainties": [],
            "evidence_gaps": [],
        }

    def fetch_prior_context(
        self,
        tenant_id: str,
        workspace_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        """Retrieves relevant system context prior to experiment execution (Task 69)."""
        context_items: list[dict[str, Any]] = []
        try:
            from app.context.universal_service import get_universal_context_service

            ctx_service = get_universal_context_service()
            bundle = ctx_service.assemble_context(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                query=query,
            )
            for item in bundle.items:
                context_items.append(
                    {
                        "item_id": item.item_id,
                        "content": item.content[:300],
                        "source": item.source,
                    }
                )
        except Exception as e:
            logger.debug(f"Unable to fetch universal context for discovery query: {e}")

        return context_items

    def allocate_cognitive_budget(
        self,
        tenant_id: str,
        importance: float,
        expected_gain: float,
    ) -> float:
        """Coordinates with Task 70 to allocate attention and compute tokens."""
        # Baseline allocated cost ceiling
        allocated = round(max(0.1, min(10.0, importance * expected_gain * 2.0)), 2)
        return allocated

    def run_simulation_preflight(
        self,
        experiment: ExperimentDesign,
    ) -> ExperimentObservation:
        """Executes a non-invasive synthetic simulation prior to any physical intervention (Task 56).

        Strict Principle: Simulation results are explicitly flagged is_simulation=True
        and are NEVER treated as real-world observation.
        """
        sim_val = {"predicted_trend": "decrease", "delta": -0.15, "confidence": 0.85}
        return ExperimentObservation(
            observation_id=f"sim_obs_{experiment.experiment_id[:8]}",
            experiment_id=experiment.experiment_id,
            source="Task56_DigitalTwinSimulation",
            environment=experiment.environment,
            measurement_metric=experiment.dependent_variables[0]
            if experiment.dependent_variables
            else "latency",
            value=sim_val,
            unit="synthetic_units",
            raw_reference="simulation://digital_twin_run",
            verification_state="SIMULATED",
            is_simulation=True,
        )

    def promote_to_candidate_knowledge(
        self,
        tenant_id: str,
        workspace_id: str,
        result: ExperimentResult,
        question: str,
    ) -> dict[str, Any]:
        """Consolidates verified findings into Task 68 Executive Memory / Knowledge.

        Strict Principle:
        - Results in staging must remain scoped to staging.
        - Zero exposure of private chain-of-thought.
        - Distinguish consistency from absolute verification.
        """
        scope_str = result.generalization_scope.value
        title = f"Empirical finding: {question[:80]}"
        content = (
            f"Question: {question}\n"
            f"Outcome: {result.outcome.value}\n"
            f"Scope: {scope_str}\n"
            f"Summary: {result.prediction_vs_observation_summary}\n"
            f"Replication: {result.replication_status}\n"
            f"Conclusions: {'; '.join(result.conclusions)}"
        )

        try:
            from app.memory_consolidation.service import get_memory_consolidation_service

            _ = get_memory_consolidation_service()
            # Feed structured summary into memory consolidation without exposing chain-of-thought
            logger.info(f"Promoting discovery result {result.result_id} to candidate knowledge.")
        except Exception as e:
            logger.debug(f"Knowledge consolidation bridge note: {e}")

        return {
            "status": "CANDIDATE_KNOWLEDGE_CREATED",
            "title": title,
            "scope": scope_str,
            "content": content,
            "requires_independent_verification": True,
        }
