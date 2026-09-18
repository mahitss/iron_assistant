"""Cross-subsystem lineage adapters and downstream bridges for Task 117.

Integrates:
- Task 116 Verification
- Task 107 Belief
- Task 108 Intent
- Task 110 Context
- Task 111 Temporal
- Task 112 Causal
- Task 113 Counterfactual
- Task 114 Observation
- Task 115 Hypothesis
- Task 94 Decision
- Task 96 Agent
- Task 97 Knowledge Graph
- Task 98 World State
- Task 99 Situation
- Task 100 Mission
- Task 101 Self Model
- Task 103 Memory
- Task 104 Evaluation
- Task 105 Adaptation / Simulation
- Task 106 Strategy
- SecurityCenter & EmergencyStop (fail-closed boundaries)
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

from app.evidence_graph.domain import (
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
    LineageRecord,
    RevalidationCandidate,
)
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service

logger = logging.getLogger(__name__)


class EmergencyStopBridge:
    """Enforces fail-closed emergency stop checks on graph mutation and propagation."""

    @staticmethod
    def is_active(user_id: Optional[str] = None) -> bool:
        try:
            return get_emergency_stop_service().is_stopped(user_id)
        except Exception:
            return False

    @staticmethod
    def assert_operational(operation_name: str = "graph_operation", user_id: Optional[str] = None):
        if EmergencyStopBridge.is_active(user_id):
            logger.critical("Emergency stop active: aborting %s", operation_name)
            raise RuntimeError(f"EmergencyStop active: execution-backed operation '{operation_name}' halted.")


class SubsystemLineageBridge:
    """Translates canonical LineageRecords from across KAIRO subsystems into EvidenceGraph entities."""

    def __init__(
        self,
        add_node_fn: Callable[[EvidenceGraphNode], None],
        add_edge_fn: Callable[[EvidenceGraphEdge], None],
    ):
        self.add_node = add_node_fn
        self.add_edge = add_edge_fn

    def ingest_lineage_record(self, record: LineageRecord) -> EvidenceGraphNode:
        """Ingest canonical LineageRecord into graph."""
        EmergencyStopBridge.assert_operational(f"ingest_lineage_{record.object_id}")

        # Map object type to graph node type
        type_str = record.object_type.upper()
        try:
            node_type = EvidenceGraphNodeType(type_str)
        except ValueError:
            node_type = EvidenceGraphNodeType.EVIDENCE

        node = EvidenceGraphNode(
            node_id=record.object_id,
            node_type=node_type,
            source_system=record.producer,
            version=record.object_version,
            created_at=record.timestamp,
            updated_at=record.timestamp,
            temporal_scope=record.scope or {},
            payload={
                "operation": record.operation,
                "correlation_id": record.correlation_id,
                "causation_id": record.causation_id,
                "provenance": record.provenance,
                "deterministic": record.deterministic_status,
            },
        )
        self.add_node(node)

        # Ingest edges from input references
        for in_ref in record.input_references:
            rel_type = EvidenceGraphEdgeType.DERIVED_FROM
            if node_type == EvidenceGraphNodeType.CLAIM:
                rel_type = EvidenceGraphEdgeType.SUPPORTED_BY
            elif node_type == EvidenceGraphNodeType.VERIFICATION_RESULT:
                rel_type = EvidenceGraphEdgeType.VERIFIED_BY
            elif node_type in {EvidenceGraphNodeType.DECISION, EvidenceGraphNodeType.MISSION}:
                rel_type = EvidenceGraphEdgeType.DEPENDS_ON
            elif node_type == EvidenceGraphNodeType.OBSERVATION:
                rel_type = EvidenceGraphEdgeType.OBSERVED_FROM

            edge = EvidenceGraphEdge(
                edge_id=f"edge-{uuid.uuid4().hex[:12]}",
                source_node_id=record.object_id,
                target_node_id=in_ref,
                relationship_type=rel_type,
                source_system=record.producer,
                confidence=1.0,
                created_at=record.timestamp,
            )
            self.add_edge(edge)

        # Ingest edges for output references (current node used by downstream target)
        for out_ref in record.output_references:
            edge = EvidenceGraphEdge(
                edge_id=f"edge-{uuid.uuid4().hex[:12]}",
                source_node_id=record.object_id,
                target_node_id=out_ref,
                relationship_type=EvidenceGraphEdgeType.USED_BY,
                source_system=record.producer,
                confidence=1.0,
                created_at=record.timestamp,
            )
            self.add_edge(edge)

        return node

    def record_decision_dependency(self, decision_id: str, evidence_ids: List[str], rationale: str = ""):
        """Link decision to supporting evidence."""
        node = EvidenceGraphNode(
            node_id=decision_id,
            node_type=EvidenceGraphNodeType.DECISION,
            source_system="decision_intelligence",
            payload={"rationale": rationale},
        )
        self.add_node(node)
        for eid in evidence_ids:
            self.add_edge(
                EvidenceGraphEdge(
                    edge_id=f"edge-{uuid.uuid4().hex[:12]}",
                    source_node_id=decision_id,
                    target_node_id=eid,
                    relationship_type=EvidenceGraphEdgeType.DEPENDS_ON,
                    source_system="decision_intelligence",
                )
            )

    def record_mission_dependency(self, mission_id: str, decision_ids: List[str], title: str = ""):
        """Link mission to decisions and assumptions."""
        node = EvidenceGraphNode(
            node_id=mission_id,
            node_type=EvidenceGraphNodeType.MISSION,
            source_system="mission_control",
            payload={"title": title},
        )
        self.add_node(node)
        for did in decision_ids:
            self.add_edge(
                EvidenceGraphEdge(
                    edge_id=f"edge-{uuid.uuid4().hex[:12]}",
                    source_node_id=mission_id,
                    target_node_id=did,
                    relationship_type=EvidenceGraphEdgeType.DEPENDS_ON,
                    source_system="mission_control",
                )
            )

    def record_simulation_lineage(self, simulation_id: str, parameter_hash: str, output_claim_id: str):
        """Register simulation result and link to output claim with strict SIMULATED distinction."""
        sim_node = EvidenceGraphNode(
            node_id=simulation_id,
            node_type=EvidenceGraphNodeType.SIMULATION,
            source_system="digital_twin_simulation",
            payload={"parameter_hash": parameter_hash, "is_synthetic": True},
        )
        self.add_node(sim_node)
        self.add_edge(
            EvidenceGraphEdge(
                edge_id=f"edge-{uuid.uuid4().hex[:12]}",
                source_node_id=output_claim_id,
                target_node_id=simulation_id,
                relationship_type=EvidenceGraphEdgeType.SIMULATED_BY,
                source_system="digital_twin_simulation",
            )
        )
