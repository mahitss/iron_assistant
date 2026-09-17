"""Core SelfModelService orchestrating internal state intelligence (Task 101).

Responsibilities:
1. Reconciles state across authoritative sources into versioned snapshots.
2. Computes strict deltas and state drift.
3. Evaluates limitations, uncertainties, and multi-dimensional readiness.
4. Provides typed query APIs for Missions (Task 100), Situations (Task 99), and Decision Intelligence (Task 96).
5. Enforces grounding verification: 100% evidence-backed, no fictional self-awareness.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.self_model.bridges import SelfModelBridges
from app.self_model.delta_engine import SelfModelDeltaEngine
from app.self_model.limitation_engine import LimitationReasoningEngine
from app.self_model.query_engine import SelfModelQueryEngine
from app.self_model.schemas import (
    CapabilityAwarenessItem,
    CapabilityReadinessState,
    GroundingVerificationResult,
    LimitationItem,
    SelfModelAnswers,
    SelfModelDelta,
    SelfModelSnapshot,
    UncertaintyItem,
)

logger = logging.getLogger("kairo.self_model.service")


class SelfModelService:
    """Master coordinator for Kairo's introspective operational model."""

    def __init__(self, db_session: Optional[AsyncSession] = None) -> None:
        self.db = db_session
        self._snapshots: deque[SelfModelSnapshot] = deque(maxlen=50)
        self._deltas: deque[SelfModelDelta] = deque(maxlen=50)
        self._current_snapshot: Optional[SelfModelSnapshot] = None

    def get_current_snapshot(self) -> SelfModelSnapshot:
        """Returns the most recent snapshot, or generates a fresh one if none exists."""
        if self._current_snapshot is None:
            return self.reconcile()
        return self._current_snapshot

    def reconcile(self) -> SelfModelSnapshot:
        """Executes full empirical state reconciliation across all authoritative subsystems."""
        runtime = SelfModelBridges.collect_runtime_state()
        resources = SelfModelBridges.collect_resource_state()
        security = SelfModelBridges.collect_security_governance()
        dependencies = SelfModelBridges.collect_dependencies()
        tools = SelfModelBridges.collect_tools()
        capabilities = SelfModelBridges.collect_capabilities(dependencies, security)

        limitations = LimitationReasoningEngine.evaluate_limitations(
            capabilities, dependencies, security, resources
        )
        uncertainties = LimitationReasoningEngine.evaluate_uncertainties(
            capabilities, dependencies, security
        )

        snap_id = f"snap_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(UTC).isoformat()

        # Temporary snapshot to calculate answers and diff
        draft_snapshot = SelfModelSnapshot(
            snapshot_id=snap_id,
            created_at=now_str,
            model_version="1.0.0",
            runtime_version=runtime.runtime_version,
            protocol_version=runtime.protocol_version,
            autonomy_mode=security.autonomy_mode,
            emergency_stop_state=security.emergency_stop_active,
            capabilities=capabilities,
            tools=tools,
            runtime=runtime,
            resources=resources,
            security_governance=security,
            dependencies=dependencies,
            limitations=limitations,
            uncertainties=uncertainties,
            confidence_score=1.0 if not security.emergency_stop_active else 0.9,
            evidence_references=[
                "CapabilityLifecycleService",
                "ToolRegistry",
                "EmergencyStopService",
                "ResourceEconomyEngine",
                "ReliabilityIntelligenceService",
            ],
        )

        # Compute delta from last snapshot
        delta = SelfModelDeltaEngine.compute_delta(self._current_snapshot, draft_snapshot)
        self._deltas.append(delta)

        # Resolve answers to all 15 questions
        answers = SelfModelQueryEngine.resolve_answers(
            capabilities=capabilities,
            tools=tools,
            resources=resources,
            security=security,
            dependencies=dependencies,
            limitations=limitations,
            uncertainties=uncertainties,
            recent_changes=delta.changes,
        )
        draft_snapshot.answers = answers

        # Save and advance state
        self._current_snapshot = draft_snapshot
        self._snapshots.append(draft_snapshot)

        self._emit_event("self_model.snapshot_created", draft_snapshot)
        return draft_snapshot

    def get_answers(self) -> SelfModelAnswers:
        """Returns answers to the 15 canonical introspective questions."""
        snapshot = self.get_current_snapshot()
        return snapshot.answers

    def get_capabilities(self) -> Dict[str, CapabilityAwarenessItem]:
        """Returns capability awareness map."""
        return self.get_current_snapshot().capabilities

    def get_capability_readiness(self, capability_id: str) -> Optional[CapabilityAwarenessItem]:
        """Returns readiness status and evidence for a specific capability."""
        return self.get_current_snapshot().capabilities.get(capability_id)

    def can_capability_run(self, capability_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Read-only feasibility inquiry for Mission Control or Decision Intelligence."""
        cap = self.get_capability_readiness(capability_id)
        if not cap:
            return False
        return cap.readiness_state == CapabilityReadinessState.READY

    def get_limitations(self) -> List[LimitationItem]:
        """Returns current evidence-backed limitations."""
        return self.get_current_snapshot().limitations

    def get_uncertainties(self) -> List[UncertaintyItem]:
        """Returns current epistemic uncertainties."""
        return self.get_current_snapshot().uncertainties

    def get_recent_deltas(self) -> List[SelfModelDelta]:
        """Returns history of state diffs."""
        return list(self._deltas)

    def get_snapshot_history(self) -> List[SelfModelSnapshot]:
        """Returns timeline of immutable snapshots."""
        return list(self._snapshots)

    def verify_grounding(self) -> GroundingVerificationResult:
        """Audit routine verifying that every self-model claim is backed by empirical telemetry."""
        snapshot = self.get_current_snapshot()
        total_claims = 0
        verified_claims = 0
        unverified = []
        violations = []

        # Verify capability claims
        for cap_id, cap in snapshot.capabilities.items():
            total_claims += 1
            if cap.evidence and len(cap.evidence) > 0:
                verified_claims += 1
            else:
                unverified.append(f"Capability '{cap_id}' lacks empirical evidence references")

            # Check invalid state combination (e.g. e_stop active but capability claimed READY)
            if snapshot.emergency_stop_state and cap.readiness_state == CapabilityReadinessState.READY:
                violations.append(
                    f"Invariant violation: Capability '{cap_id}' is marked READY during active EmergencyStop"
                )

        # Verify limitation claims
        for lim in snapshot.limitations:
            total_claims += 1
            if lim.evidence and lim.reason:
                verified_claims += 1
            else:
                unverified.append(f"Limitation '{lim.limitation_id}' lacks supporting evidence")

        is_grounded = len(violations) == 0 and len(unverified) == 0
        verdict = "GROUNDED" if is_grounded else "GROUNDING_BREACH_DETECTED"

        return GroundingVerificationResult(
            is_grounded=is_grounded,
            total_claims=total_claims,
            verified_claims=verified_claims,
            unverified_claims=unverified,
            violations=violations,
            verdict=verdict,
        )

    def _emit_event(self, event_type: str, snapshot: SelfModelSnapshot) -> None:
        """Emits event to observability / EventBus."""
        try:
            logger.debug("Emitted self_model event '%s' for snapshot %s", event_type, snapshot.snapshot_id)
        except Exception:
            pass


_global_self_model_service: Optional[SelfModelService] = None


def get_self_model_service(db_session: Optional[AsyncSession] = None) -> SelfModelService:
    """Returns singleton SelfModelService instance."""
    global _global_self_model_service
    if _global_self_model_service is None:
        _global_self_model_service = SelfModelService(db_session=db_session)
    elif db_session is not None:
        _global_self_model_service.db = db_session
    return _global_self_model_service
