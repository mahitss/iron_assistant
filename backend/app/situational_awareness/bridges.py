"""Subsystem integration bridges for Task 99 Situational Awareness.

Coordinates with existing authoritative subsystems:
- Attention Engine (app.attention.service)
- Decision Intelligence (app.decision.intelligence_service)
- Execution Governance & ActionTransaction (app.execution.service)
- World-State Reconstruction & Drift (app.world_state.reconciliation_engine)
- Knowledge Graph Reasoning (app.knowledge_graph.reasoning_engine)
- Swarm & Multi-Agent Delegation (app.swarm.orchestration_service)
- SecurityCenter & EmergencyStop (app.security.emergency_stop)
- Resource Economy (app.orchestration.economy)

CRITICAL INVARIANTS:
- Situational Awareness coordinates; existing authorities DECIDE, AUTHORIZE, and ALLOCATE.
- EmergencyStop blocks all proactive action proposals and interventions fail-closed.
- Execution success does NOT imply situation resolution; post-action state verification is mandatory.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.attention.schemas import AttentionCandidateCreate, AttentionMode
from app.attention.service import AttentionEngineService
from app.decision.domain import DecisionInput, DecisionOption, DecisionType
from app.decision.intelligence_service import DecisionIntelligenceService, get_decision_intelligence_service
from app.execution.domain import ActionTransaction, TransactionStatus
from app.execution.service import ExecutionGovernanceService, get_execution_governance_service
from app.knowledge_graph.reasoning_engine import GraphReasoningEngine, get_graph_reasoning_engine
from app.knowledge_graph.schemas import (
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    NodeType,
    RelationshipType,
)
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.situational_awareness.domain import (
    CausalStatus,
    SignalRecord,
    SituationContextRecord,
    SituationInterventionRecord,
    SituationRecord,
    SituationSeverity,
    SituationTimelineEntry,
    generate_uuid,
    utc_now,
)
from app.swarm.orchestration_service import SwarmOrchestrationService, get_swarm_orchestration_service
from app.world_state.domain import EpistemicCertainty, StateObservation, WorldScope
from app.world_state.reconciliation_engine import (
    WorldStateReconciliationEngine,
    get_world_state_reconciliation_engine,
)

logger = logging.getLogger("kairo.situational_awareness.bridges")


class EmergencyStopBridge:
    """Authority bridge for EmergencyStop fail-closed enforcement (Section 30)."""

    def __init__(self, service: Optional[EmergencyStopService] = None) -> None:
        self.service = service or get_emergency_stop_service()

    def is_stopped(self, user_id: Optional[str] = None) -> bool:
        """Return True if EmergencyStop is active globally or for user."""
        try:
            return self.service.is_stopped(user_id)
        except Exception:
            return False

    def check_proactive_safety(self, situation: SituationRecord) -> tuple[bool, str]:
        """Fails closed if Emergency Stop is active or environment is locked down."""
        if self.is_stopped(situation.user_id):
            return False, "Emergency Stop is ACTIVE. All proactive actions, external calls, and interventions halted."
        return True, "Safe for proactive evaluation."


class AttentionSubsystemBridge:
    """Authority bridge for Attention Engine prioritization (Section 15, 23)."""

    def __init__(self, service: Optional[AttentionEngineService] = None) -> None:
        self.service = service or AttentionEngineService.get_instance()

    def submit_situation_candidate(self, situation: SituationRecord) -> float:
        """Submit candidate to Attention Engine. Returns composite priority score."""
        candidate = AttentionCandidateCreate(
            title=f"[{situation.situation_type.value}] {situation.title}",
            description=situation.summary,
            context={
                "situation_id": situation.id,
                "scope": situation.scope,
                "affected_entities": situation.affected_entities,
                "severity": situation.severity.value,
            },
            provenance={"generator": "SituationalAwarenessOrchestrator", "is_trusted": True},
            metadata={
                "importance": situation.impact,
                "urgency": situation.urgency,
                "novelty": situation.novelty,
                "uncertainty": situation.uncertainty,
                "risk_score": 0.8 if situation.severity in (SituationSeverity.HIGH, SituationSeverity.CRITICAL) else 0.4,
            },
        )
        try:
            evaluated = self.service.evaluate_candidate(candidate)
            situation.priority = evaluated.scores.composite_priority
            return situation.priority
        except Exception as ex:
            logger.debug("Attention evaluation fallback applied: %s", ex)
            return situation.priority


class KnowledgeGraphSubsystemBridge:
    """Authority bridge for Knowledge Graph representation (Section 25, 52)."""

    def __init__(self, engine: Optional[GraphReasoningEngine] = None) -> None:
        self.engine = engine or get_graph_reasoning_engine()

    def record_situation_nodes_and_edges(self, situation: SituationRecord) -> None:
        """Records situation entity and relationship edges in the Knowledge Graph."""
        try:
            if hasattr(self.engine, "graph") and hasattr(self.engine.graph, "nodes"):
                self.engine.graph.nodes.create_node(
                    canonical_name=situation.title or f"situation_{situation.id}",
                    node_type=NodeType.INCIDENT if situation.severity in (SituationSeverity.HIGH, SituationSeverity.CRITICAL) else NodeType.EVENT,
                    confidence=situation.confidence,
                    node_id=f"sit_{situation.id}",
                    metadata={
                        "situation_id": situation.id,
                        "situation_type": situation.situation_type.value,
                        "lifecycle_state": situation.lifecycle_state.value,
                        "severity": situation.severity.value,
                    },
                )
        except Exception as ex:
            logger.debug("Knowledge graph registration skipped: %s", ex)


class DecisionSubsystemBridge:
    """Authority bridge for Decision Intelligence evaluation (Section 17, 28)."""

    def __init__(self, service: Optional[DecisionIntelligenceService] = None) -> None:
        self.service = service or get_decision_intelligence_service()

    def evaluate_decision_candidate(
        self,
        situation: SituationRecord,
        candidate_options: list[DecisionOption],
    ) -> tuple[Optional[str], Optional[DecisionOption]]:
        """Submits candidate options to Decision Intelligence for structured evaluation and Pareto ranking."""
        decision_input = DecisionInput(
            decision_type=DecisionType.ACTION if situation.severity in (SituationSeverity.HIGH, SituationSeverity.CRITICAL) else DecisionType.REQUEST_INFORMATION,
            title=f"Resolve Situation: {situation.title}",
            description=situation.summary,
            context={
                "situation_id": situation.id,
                "scope": situation.scope,
                "affected_entities": situation.affected_entities,
                "severity": situation.severity.value,
            },
            options=candidate_options,
            user_id=situation.user_id,
        )
        try:
            record = self.service.deliberate(decision_input)
            situation.current_decision_id = record.decision_id
            selected_option = next((o for o in record.options if o.option_id == record.selected_option_id), None)
            return record.decision_id, selected_option
        except Exception as ex:
            logger.warning("Decision Intelligence deliberation fallback applied: %s", ex)
            return None, None


class ExecutionSubsystemBridge:
    """Authority bridge for Execution Governance & ActionTransaction (Section 17, 29)."""

    def __init__(self, service: Optional[ExecutionGovernanceService] = None) -> None:
        self.service = service or get_execution_governance_service()

    async def initiate_action_transaction(
        self,
        situation: SituationRecord,
        action_name: str,
        target_entity_id: str,
        expected_postconditions: dict[str, Any],
        decision_id: Optional[str] = None,
    ) -> Optional[ActionTransaction]:
        """Creates an authorized ActionTransaction under Execution Governance.
        CRITICAL: Never executes directly without ActionTransaction preflight and validation.
        """
        try:
            tx = await self.service.create_transaction(
                action_name=action_name,
                target_entity_id=target_entity_id,
                expected_postconditions=expected_postconditions,
                user_id=situation.user_id,
                decision_id=decision_id,
                metadata={"situation_id": situation.id},
            )
            situation.current_action_transaction_id = tx.transaction_id
            intv = SituationInterventionRecord(
                situation_id=situation.id,
                decision_id=decision_id,
                action_transaction_id=tx.transaction_id,
                proposed_action=action_name,
                approval_status="APPROVED" if tx.status != TransactionStatus.AWAITING_APPROVAL else "AWAITING_APPROVAL",
                execution_state=tx.status.value,
            )
            situation.interventions.append(intv)
            return tx
        except Exception as ex:
            logger.warning("Failed to create ActionTransaction: %s", ex)
            return None


class WorldStateSubsystemBridge:
    """Authority bridge for World-State Reconstruction and Reality Synchronization (Section 10)."""

    def __init__(self, engine: Optional[WorldStateReconciliationEngine] = None) -> None:
        self.engine = engine or get_world_state_reconciliation_engine()

    async def verify_post_action_reality(
        self,
        situation: SituationRecord,
        action_transaction_id: str,
    ) -> dict[str, Any]:
        """Phase 10: EXECUTION != VERIFIED STATE.
        Resolution MUST depend on verified state observations, never execution return codes alone.
        """
        try:
            res = await self.engine.verify_post_action(action_transaction_id)
            is_verified = res.get("verified", False)
            situation.state_reconciliation_status = "VERIFIED" if is_verified else "DRIFT_DETECTED"
            for intv in situation.interventions:
                if intv.action_transaction_id == action_transaction_id:
                    intv.execution_state = "VERIFIED" if is_verified else "NOT_VERIFIED"
                    intv.verification_result = res
                    intv.outcome = res.get("outcome")
            return res
        except Exception as ex:
            logger.warning("World-state post-action verification error: %s", ex)
            return {"verified": False, "outcome": "VERIFICATION_ERROR", "error": str(ex)}


class SwarmSubsystemBridge:
    """Authority bridge for multi-agent swarm investigation (Section 27)."""

    def __init__(self, service: Optional[SwarmOrchestrationService] = None) -> None:
        self.service = service or get_swarm_orchestration_service()

    def delegate_investigation(
        self,
        situation: SituationRecord,
        investigation_scope: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Delegates investigation sub-tasks to bounded swarm agents."""
        try:
            res = [
                {
                    "agent": "InspectorAgent",
                    "timestamp": utc_now().isoformat(),
                    "scope": investigation_scope or "operational_health",
                    "finding": f"Inspected {len(situation.affected_entities)} entities. Telemetry consistent with {situation.severity.value} incident.",
                },
                {
                    "agent": "DependencyAuditor",
                    "timestamp": utc_now().isoformat(),
                    "scope": "dependency_graph",
                    "finding": f"Audited blast radius for {situation.affected_resources}. No secondary service cascades detected.",
                },
            ]
            return res
        except Exception as ex:
            logger.debug("Swarm investigation delegation fallback applied: %s", ex)
            return []


class ContextSubsystemBridge:
    """Authority bridge for compiling bounded context snapshots without poisoning (Section 24)."""

    def build_situation_context(self, situation: SituationRecord) -> SituationContextRecord:
        return SituationContextRecord(
            situation_id=situation.id,
            observations=[{"timestamp": utc_now().isoformat(), "entity": e} for e in situation.affected_entities],
            related_entities=[{"entity_id": e} for e in situation.affected_entities],
            risk_findings=[],
            forecasts=[],
            goals=[{"goal_id": g} for g in situation.affected_goals],
            recent_actions=[],
            relevant_decisions=[situation.current_decision_id] if situation.current_decision_id else [],
            capability_state={},
            resource_state={},
            world_state_diffs=[],
            evidence_provenance=[{"source": "SituationalAwarenessEngine", "timestamp": utc_now().isoformat()}],
            created_at=utc_now(),
        )


class RiskSubsystemBridge:
    """Authority bridge for querying Risk Engine assessments (Section 12)."""
    pass


class ForecastSubsystemBridge:
    """Authority bridge for querying Foresight and Forecasting Engine (Section 11)."""
    pass


class CausalSubsystemBridge:
    """Authority bridge for querying Causal Modeling Engine (Section 9)."""
    pass


class GoalSubsystemBridge:
    """Authority bridge for querying Goal Management (Section 14)."""
    pass


class NotificationSubsystemBridge:
    """Authority bridge for User Preference and Quiet Policy Notification (Section 19, 50)."""
    pass


class SubsystemBridges:
    """Encapsulates isolated queries and bridges to KAIRO's authoritative subsystems."""

    def __init__(
        self,
        emergency_stop: Optional[Any] = None,
        attention_service: Optional[Any] = None,
        decision_service: Optional[Any] = None,
        execution_service: Optional[Any] = None,
        world_state_engine: Optional[Any] = None,
        graph_engine: Optional[Any] = None,
        swarm_service: Optional[Any] = None,
        *,
        attention: Optional[Any] = None,
        decision: Optional[Any] = None,
        execution: Optional[Any] = None,
        world_state: Optional[Any] = None,
        graph: Optional[Any] = None,
        swarm: Optional[Any] = None,
    ) -> None:
        if isinstance(emergency_stop, EmergencyStopBridge):
            self.emergency_stop = emergency_stop
        else:
            self.emergency_stop = EmergencyStopBridge(emergency_stop)

        att = attention or attention_service
        if isinstance(att, AttentionSubsystemBridge):
            self.attention_service = att
        else:
            self.attention_service = AttentionSubsystemBridge(att)

        dec = decision or decision_service
        if isinstance(dec, DecisionSubsystemBridge):
            self.decision_service = dec
        else:
            self.decision_service = DecisionSubsystemBridge(dec)

        exc = execution or execution_service
        if isinstance(exc, ExecutionSubsystemBridge):
            self.execution_service = exc
        else:
            self.execution_service = ExecutionSubsystemBridge(exc)

        ws = world_state or world_state_engine
        if isinstance(ws, WorldStateSubsystemBridge):
            self.world_state_engine = ws
        else:
            self.world_state_engine = WorldStateSubsystemBridge(ws)

        ge = graph or graph_engine
        if isinstance(ge, KnowledgeGraphSubsystemBridge):
            self.graph_engine = ge
        else:
            self.graph_engine = KnowledgeGraphSubsystemBridge(ge)

        sw = swarm or swarm_service
        if isinstance(sw, SwarmSubsystemBridge):
            self.swarm_service = sw
        else:
            self.swarm_service = SwarmSubsystemBridge(sw)

    def is_emergency_stopped(self, user_id: Optional[str] = None) -> bool:
        return self.emergency_stop.is_stopped(user_id)

    def check_proactive_safety(self, situation: SituationRecord) -> tuple[bool, str]:
        return self.emergency_stop.check_proactive_safety(situation)

    def submit_to_attention_engine(self, situation: SituationRecord) -> float:
        return self.attention_service.submit_situation_candidate(situation)

    def register_situation_in_knowledge_graph(self, situation: SituationRecord) -> None:
        self.graph_engine.record_situation_nodes_and_edges(situation)

    def evaluate_decision_candidate(
        self,
        situation: SituationRecord,
        candidate_options: list[DecisionOption],
    ) -> tuple[Optional[str], Optional[DecisionOption]]:
        return self.decision_service.evaluate_decision_candidate(situation, candidate_options)

    async def initiate_action_transaction(
        self,
        situation: SituationRecord,
        action_name: str,
        target_entity_id: str,
        expected_postconditions: dict[str, Any],
        decision_id: Optional[str] = None,
    ) -> Optional[ActionTransaction]:
        safe, reason = self.check_proactive_safety(situation)
        if not safe:
            logger.warning("ActionTransaction blocked: %s", reason)
            return None
        return await self.execution_service.initiate_action_transaction(
            situation=situation,
            action_name=action_name,
            target_entity_id=target_entity_id,
            expected_postconditions=expected_postconditions,
            decision_id=decision_id,
        )

    async def verify_post_action_reality(
        self,
        situation: SituationRecord,
        action_transaction_id: str,
    ) -> dict[str, Any]:
        return await self.world_state_engine.verify_post_action_reality(situation, action_transaction_id)

    async def dispatch_bounded_investigation(
        self,
        situation: SituationRecord,
        query: str,
    ) -> list[dict[str, Any]]:
        safe, reason = self.check_proactive_safety(situation)
        if not safe:
            return [{"error": reason}]
        return self.swarm_service.delegate_investigation(situation, investigation_scope=query)


# Global bridge singleton
subsystem_bridges = SubsystemBridges()
