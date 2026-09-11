"""Self-Model Management, Capability Awareness, and Limitation Representation (Task 67)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.self_audit.schemas import (
    CapabilityState,
    ConfidenceCalibrationState,
    MetacognitiveState,
    SelfKnowledgeType,
    SelfModel,
)

logger = logging.getLogger("kairo.self_audit.self_model")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SelfModelManager:
    """Maintains an explicit, verifiable operational self-model of Kairo's internal state (Spec 3, 4, 5)."""

    def __init__(self) -> None:
        self._models: dict[str, SelfModel] = {}

    def get_or_create_self_model(self, tenant_id: str = "default") -> SelfModel:
        """Retrieve active self-model or initialize a baseline operational model."""
        if tenant_id not in self._models:
            model = SelfModel(
                tenant_id=tenant_id,
                capabilities={
                    "code_execution": CapabilityState.CAPABILITY_AVAILABLE,
                    "web_search": CapabilityState.CAPABILITY_AVAILABLE,
                    "database_access": CapabilityState.CAPABILITY_AVAILABLE,
                    "production_deployment": CapabilityState.CAPABILITY_DEGRADED,  # Gated by approval
                    "secret_rotation": CapabilityState.CAPABILITY_UNAVAILABLE,  # Requires elevated human authority
                },
                limitations=[
                    "Cannot execute mutations without explicit authorization.",
                    "Stale knowledge beyond trained checkpoints requires empirical verification.",
                    "Cannot bypass SecurityCenter or PolicyEngine guardrails.",
                    "Single-agent dialectic has blind spots; requires swarm for high-impact decisions.",
                    "Cannot claim factual truth without verified empirical evidence.",
                ],
                active_goals=[],
                active_missions=[],
                known_dependencies=["database", "redis", "llm_gateway", "verification_engine"],
                current_state=MetacognitiveState.CONFIDENT,
                uncertainties=[],
                known_failure_modes=[
                    "Transient latency spikes under concurrency.",
                    "Premature convergence on first viable hypothesis.",
                    "Underestimation of deployment duration.",
                ],
                performance_metrics={
                    "accuracy_rate": 0.92,
                    "verification_coverage": 0.88,
                    "mean_latency_ms": 145.0,
                },
                calibration=ConfidenceCalibrationState.WELL_CALIBRATED,
                resource_state={"cpu_pct": 24.5, "memory_pct": 38.0, "active_workers": 4},
                tool_state={"tools_registered": 42, "failing_tools": 0},
                model_state={"active_model": "gemini-flash", "context_window_tokens": 1000000},
                risk_state={"composite_risk": 0.15, "open_vulnerabilities": 0},
                provenance={"initialized_by": "system_bootstrap", "version": 1},
            )
            self._models[tenant_id] = model

        return self._models[tenant_id]

    def update_capability_state(
        self,
        capability_name: str,
        state: CapabilityState,
        tenant_id: str = "default",
    ) -> SelfModel:
        """Update operational capability state with authorization awareness (Spec 4).

        Invariant: Do not claim 'I can do X' merely because a tool exists.
        """
        model = self.get_or_create_self_model(tenant_id)
        model.capabilities[capability_name] = state
        model.version += 1
        model.timestamp = _now_utc()
        logger.info(
            "CAPABILITY_UPDATED: tenant=%s capability=%s state=%s",
            tenant_id,
            capability_name,
            state.value,
        )
        return model

    def register_limitation(self, limitation_description: str, tenant_id: str = "default") -> SelfModel:
        """Explicitly represent operational limitations (Spec 5)."""
        model = self.get_or_create_self_model(tenant_id)
        if limitation_description not in model.limitations:
            model.limitations.append(limitation_description)
            model.version += 1
            model.timestamp = _now_utc()
        return model

    def update_metacognitive_state(
        self,
        new_state: MetacognitiveState,
        reason: str = "",
        tenant_id: str = "default",
    ) -> SelfModel:
        """Transition high-level metacognitive awareness state (Spec 92)."""
        model = self.get_or_create_self_model(tenant_id)
        prev = model.current_state
        model.current_state = new_state
        model.version += 1
        model.timestamp = _now_utc()
        model.provenance["last_state_transition"] = {
            "from": prev.value,
            "to": new_state.value,
            "reason": reason,
            "at": _now_utc().isoformat(),
        }
        logger.info(
            "METACOGNITIVE_STATE_TRANSITION: tenant=%s from=%s to=%s reason=%s",
            tenant_id,
            prev.value,
            new_state.value,
            reason,
        )
        return model

    def update_active_missions(
        self,
        mission_ids: list[str],
        tenant_id: str = "default",
    ) -> SelfModel:
        """Synchronize active missions and goals (integrating with Task 66)."""
        model = self.get_or_create_self_model(tenant_id)
        model.active_missions = list(mission_ids)
        model.version += 1
        model.timestamp = _now_utc()
        return model

    def classify_knowledge(
        self, statement: str, evidence_count: int, is_inferred: bool = False
    ) -> SelfKnowledgeType:
        """Classify self-knowledge into strict epistemic types (Spec 6).

        Invariant: Never collapse INFERRED, PREDICTED, or ASSUMED into KNOWN or OBSERVED.
        """
        if evidence_count >= 2 and not is_inferred:
            return SelfKnowledgeType.KNOWN
        elif evidence_count == 1 and not is_inferred:
            return SelfKnowledgeType.OBSERVED
        elif is_inferred and evidence_count > 0:
            return SelfKnowledgeType.INFERRED
        elif "will" in statement.lower() or "forecast" in statement.lower():
            return SelfKnowledgeType.PREDICTED
        elif "assume" in statement.lower() or "suppose" in statement.lower():
            return SelfKnowledgeType.ASSUMED
        elif evidence_count == 0:
            return SelfKnowledgeType.UNKNOWN
        return SelfKnowledgeType.ESTIMATED
