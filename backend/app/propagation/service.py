"""Master service orchestrator for systemic risk propagation and cross-subsystem integration (Task 75)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional, Set

from app.events.bus import event_bus
from app.events.schemas import Event
from app.propagation.bottlenecks import BottleneckAnalyzer, default_bottleneck_analyzer
from app.propagation.cascade import CascadeDetector, default_cascade_detector
from app.propagation.resilience import ResilienceEngine, default_resilience_engine
from app.propagation.schemas import (
    BottleneckNode,
    CascadeChain,
    CascadeStatus,
    CascadeType,
    ContainmentBoundary,
    DirectEffect,
    ImpactDimensions,
    MitigationRecommendation,
    PropagationAnalysis,
    PropagationEdge,
    PropagationScope,
    ResilienceAssessment,
    SecondOrderEffect,
    SinglePointOfFailure,
    TriggerType,
    UncertaintyBreakdown,
    generate_uuid,
    utc_now,
)
from app.propagation.snapshots import GraphSnapshot, GraphSnapshotEngine, default_snapshot_engine
from app.propagation.traversal import BoundedPropagationTraverser, TraversalResult, default_traverser

logger = logging.getLogger("kairo.propagation.service")


class PropagationService:
    """Master orchestrator integrating topological traversal, cascade detection, resilience, and early warnings."""

    def __init__(
        self,
        snapshot_engine: Optional[GraphSnapshotEngine] = None,
        traverser: Optional[BoundedPropagationTraverser] = None,
        cascade_detector: Optional[CascadeDetector] = None,
        bottleneck_analyzer: Optional[BottleneckAnalyzer] = None,
        resilience_engine: Optional[ResilienceEngine] = None,
    ) -> None:
        self.snapshot_engine = snapshot_engine or default_snapshot_engine
        self.traverser = traverser or default_traverser
        self.cascade_detector = cascade_detector or default_cascade_detector
        self.bottleneck_analyzer = bottleneck_analyzer or default_bottleneck_analyzer
        self.resilience_engine = resilience_engine or default_resilience_engine

        # In-memory ledgers: analysis_id -> PropagationAnalysis
        self._analyses: Dict[str, PropagationAnalysis] = {}
        # active cascades: fingerprint -> CascadeChain
        self._active_cascades: Dict[str, CascadeChain] = {}

    def analyze_propagation(
        self,
        origin_entity: str,
        trigger: str,
        trigger_type: TriggerType = TriggerType.STATE_CHANGE,
        scope: PropagationScope = PropagationScope.SERVICE,
        tenant_id: str = "default_tenant",
        snapshot_id: Optional[str] = None,
        custom_edges: Optional[List[PropagationEdge]] = None,
        custom_entities: Optional[Dict[str, Dict[str, Any]]] = None,
        initial_impact: Optional[ImpactDimensions] = None,
        initial_confidence: float = 0.9,
        regime_factor: float = 1.0,
        critical_path_entities: Optional[Set[str]] = None,
        as_of_timestamp: Optional[datetime] = None,
    ) -> PropagationAnalysis:
        """Run full end-to-end systemic propagation analysis (Spec 3, 4)."""
        # Step 1: Resolve or create snapshot
        if snapshot_id and self.snapshot_engine.get_snapshot(snapshot_id):
            snapshot = self.snapshot_engine.get_snapshot(snapshot_id)  # type: ignore
        else:
            snapshot = self.snapshot_engine.create_snapshot(
                tenant_id=tenant_id,
                entities=custom_entities,
                edges=custom_edges,
                as_of_timestamp=as_of_timestamp,
                source_references=["propagation_request"],
            )

        # Step 2: Execute bounded traversal (Spec 7-10)
        traversal_res = self.traverser.traverse(
            origin_entity=origin_entity,
            snapshot=snapshot,
            initial_confidence=initial_confidence,
            initial_impact=initial_impact,
            regime_factor=regime_factor,
        )

        # Step 3: Cascade detection & classification (Spec 11, 12, 29)
        cascades = self.cascade_detector.detect_cascades(
            traversal_result=traversal_res,
            trigger_type=trigger_type,
        )

        # Register active cascades
        for c in cascades:
            self._active_cascades[c.fingerprint] = c

        # Step 4: Bottlenecks and SPoFs (Spec 13, 14, 15)
        bottlenecks, spofs = self.bottleneck_analyzer.analyze(
            snapshot=snapshot,
            critical_path_entities=critical_path_entities,
        )

        # Step 5: Resilience & Containment assessment (Spec 16, 30)
        resilience = self.resilience_engine.assess_resilience(
            snapshot=snapshot,
            traversal_result=traversal_res,
        )

        # Step 6: Advisory mitigation candidates (Spec 31, 71)
        mitigations = self.resilience_engine.generate_mitigations(
            traversal_result=traversal_res,
            resilience=resilience,
        )

        # Step 7: Uncertainty breakdown calculation (Spec 27)
        max_depth = max((m.get("depth", 0) for m in traversal_res.visited_nodes.values()), default=0)
        uncertainty = UncertaintyBreakdown(
            epistemic_uncertainty=0.10,
            aleatoric_uncertainty=0.05,
            depth_penalty=round(max_depth * 0.05, 3),
            missing_edge_penalty=0.0 if traversal_res.is_topology_complete else 0.15,
            model_disagreement_variance=0.0,
            composite_uncertainty=round(
                min(0.95, 0.15 + (max_depth * 0.05) + (0.15 if not traversal_res.is_topology_complete else 0.0)),
                3,
            ),
        )

        analysis_id = generate_uuid()
        fingerprint = f"prop_{origin_entity}_{trigger_type.value}_{len(cascades)}"

        analysis = PropagationAnalysis(
            propagation_id=analysis_id,
            tenant_id=tenant_id,
            scope=scope,
            trigger=trigger,
            trigger_type=trigger_type,
            origin_entity=origin_entity,
            origin_state={"status": "TRIGGERED", "trigger": trigger},
            graph_snapshot=snapshot.to_reference(),
            analysis_time=utc_now(),
            horizon="MEDIUM",
            propagation_depth=max_depth,
            confidence=round(max(0.1, 1.0 - uncertainty.composite_uncertainty), 3),
            uncertainty=uncertainty,
            assumptions=traversal_res.assumptions,
            status=CascadeStatus.PROJECTED,
            direct_effects=traversal_res.direct_effects,
            second_order_effects=traversal_res.second_order_effects,
            cascades=cascades,
            bottlenecks=bottlenecks,
            single_points_of_failure=spofs,
            resilience_assessment=resilience,
            containment_options=resilience.containment_boundaries,
            mitigation_candidates=mitigations,
            fingerprint=fingerprint,
            provenance={
                "snapshot_id": snapshot.snapshot_id,
                "traversal_duration_seconds": traversal_res.duration_seconds,
                "engine": "BoundedPropagationTraverser",
            },
            is_truncated=traversal_res.is_truncated,
            truncation_reason=traversal_res.truncation_reason,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        self._analyses[analysis_id] = analysis

        # Emit audit event asynchronously if bus available (Spec 64)
        try:
            event_bus.publish(
                Event(
                    event_type="propagation.analysis_created",
                    payload={
                        "propagation_id": analysis_id,
                        "origin_entity": origin_entity,
                        "cascades_count": len(cascades),
                        "resilience_score": resilience.systemic_resilience_score,
                    },
                    tenant_id=tenant_id,
                )
            )
        except Exception as e:
            logger.debug("Event emission bypassed or not registered: %s", e)

        logger.info(
            "Completed propagation analysis %s for origin '%s': %d direct, %d 2nd-order, %d cascades, resilience=%.2f",
            analysis_id, origin_entity, len(traversal_res.direct_effects),
            len(traversal_res.second_order_effects), len(cascades), resilience.systemic_resilience_score,
        )
        return analysis

    def get_analysis(self, analysis_id: str) -> Optional[PropagationAnalysis]:
        return self._analyses.get(analysis_id)

    def list_active_cascades(self, tenant_id: str = "default_tenant") -> List[CascadeChain]:
        return list(self._active_cascades.values())

    def get_explanation(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Produce structured, human-interpretable explanation of propagation path (Spec 54)."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            return None

        explanation_steps = []
        explanation_steps.append({
            "stage": "TRIGGER",
            "entity": analysis.origin_entity,
            "description": f"Initial trigger: {analysis.trigger} ({analysis.trigger_type.value})",
        })

        for d in analysis.direct_effects:
            explanation_steps.append({
                "stage": "DIRECT_EFFECT",
                "entity": d.target_entity,
                "relationship": d.relationship_type.value,
                "epistemic": d.epistemic_category.value,
                "confidence": d.confidence,
                "expected_impact": d.impact.operational_impact,
                "delay_seconds": d.temporal_delay.expected_delay_seconds,
            })

        for s in analysis.second_order_effects:
            explanation_steps.append({
                "stage": "SECOND_ORDER_EFFECT",
                "entity": s.target_entity,
                "via": s.intermediate_entity,
                "explanation": s.explanation,
                "confidence": s.confidence,
            })

        for c in analysis.cascades:
            explanation_steps.append({
                "stage": "CASCADE_CHAIN",
                "type": c.cascade_type.value,
                "path": " -> ".join(c.nodes),
                "likelihood": c.likelihood,
                "amplification": c.amplification_detected,
            })

        return {
            "propagation_id": analysis_id,
            "origin_entity": analysis.origin_entity,
            "steps": explanation_steps,
            "resilience_summary": analysis.resilience_assessment.findings,
            "assumptions": analysis.assumptions,
        }

    def synthesize_early_warning_recommendation(
        self,
        analysis_id: str,
    ) -> Dict[str, Any]:
        """Integrate with Task 74 Early Warning: escalate severity based on downstream blast radius (Spec 21)."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            return {"recommended_warning_level": "WATCH", "rationale": "Analysis not found"}

        has_critical_spof = any(s.criticality == "CRITICAL" for s in analysis.single_points_of_failure)
        cascade_count = len(analysis.cascades)
        resilience_score = analysis.resilience_assessment.systemic_resilience_score

        # Interpretable escalation rule (Spec 21)
        if has_critical_spof and cascade_count >= 2 and resilience_score < 0.4:
            recommended_level = "CRITICAL"
            rationale = "Critical SPoF involved with multiple projected cascades and low systemic resilience."
        elif cascade_count >= 2 or has_critical_spof:
            recommended_level = "WARNING"
            rationale = "Multiple dependent cascades or single point of failure exposed downstream."
        elif cascade_count == 1:
            recommended_level = "ADVISORY"
            rationale = "Single downstream cascade projected; monitor leading indicator stability."
        else:
            recommended_level = "WATCH"
            rationale = "Local effect contained; no systemic cascade detected."

        return {
            "propagation_id": analysis_id,
            "recommended_warning_level": recommended_level,
            "rationale": rationale,
            "downstream_exposure_count": len(analysis.direct_effects) + len(analysis.second_order_effects),
            "resilience_score": resilience_score,
            "is_advisory_only": True,
        }

    def summarize_for_attention(
        self,
        analysis_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Summarize multi-node cascade into a single digestible insight for Attention Engine (Spec 40, 41)."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            return None

        total_affected = len(analysis.direct_effects) + len(analysis.second_order_effects)
        if total_affected == 0:
            return None

        summary_text = (
            f"Upstream event at '{analysis.origin_entity}' may propagate to {total_affected} downstream components "
            f"across {len(analysis.cascades)} cascade paths (Resilience: {analysis.resilience_assessment.systemic_resilience_score:.2f})."
        )

        return {
            "title": f"Systemic Risk: {analysis.origin_entity}",
            "summary": summary_text,
            "urgency": 0.85 if any(s.criticality == "CRITICAL" for s in analysis.single_points_of_failure) else 0.60,
            "affected_component_count": total_affected,
            "key_bottlenecks": [b.name or b.entity_id for b in analysis.bottlenecks[:3]],
            "is_truncated": analysis.is_truncated,
        }


# Global default service instance
default_propagation_service = PropagationService()
