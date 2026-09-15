"""Blast-radius analysis integrating with Task 75 Risk Propagation for Kairo Reliability (Task 88)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from app.reliability.taxonomy import FailureSeverity, FailureType

logger = logging.getLogger("kairo.reliability.blast_radius")


class BlastRadiusAnalyzer:
    """Computes systemic impact and blast radius across subsystems, workflows, tasks, and executions."""

    def __init__(self, propagation_service: Optional[Any] = None) -> None:
        self._propagation_service = propagation_service

    def _get_propagation_service(self) -> Any:
        if self._propagation_service is None:
            try:
                from app.propagation.service import PropagationService
                self._propagation_service = PropagationService()
            except Exception as e:
                logger.debug("PropagationService lazy initialization notice: %s", e)
        return self._propagation_service

    async def calculate_blast_radius(
        self,
        component: str,
        failure_type: FailureType,
        severity: FailureSeverity,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Calculates blast radius integrating with Task 75 Risk Propagation."""
        meta = metadata or {}
        subsystem = component.lower()

        # Extract contextually declared targets
        active_workflows = list(meta.get("active_workflows", []))
        active_tasks = list(meta.get("active_tasks", []))
        active_tools = list(meta.get("active_tools", []))
        active_executions = list(meta.get("executions", []))
        active_resources = list(meta.get("resources", []))

        # Default impact dimensions
        systemic_score = 0.2
        if severity == FailureSeverity.P0:
            systemic_score = 1.0
        elif severity == FailureSeverity.P1:
            systemic_score = 0.75
        elif severity == FailureSeverity.P2:
            systemic_score = 0.5
        elif severity == FailureSeverity.P3:
            systemic_score = 0.25

        dependent_services: Set[str] = set()
        second_order_cascades: List[str] = []

        # Integrate with Task 75 Propagation Engine
        prop_svc = self._get_propagation_service()
        if prop_svc is not None:
            try:
                from app.propagation.schemas import PropagationScope, TriggerType
                # Invoke existing risk propagation analysis
                analysis = await prop_svc.analyze_propagation(
                    trigger_entity=component,
                    trigger_type=TriggerType.SUBSYSTEM_DEGRADATION,
                    initial_impact={"availability": systemic_score},
                    scope=PropagationScope.SYSTEM_WIDE if severity in (FailureSeverity.P0, FailureSeverity.P1) else PropagationScope.LOCAL_CLUSTER,
                    metadata={"failure_type": failure_type.value},
                )
                if analysis:
                    for aff in analysis.affected_entities:
                        dependent_services.add(aff.entity_id)
                    for soe in analysis.second_order_effects:
                        second_order_cascades.append(f"{soe.source_entity}->{soe.target_entity}: {soe.effect_type}")
                    systemic_score = max(systemic_score, analysis.cascade_potential)
            except Exception as exc:
                logger.debug("Fallback to topological heuristic for blast radius: %s", exc)

        # Static topological dependency fallback if propagation service is unavailable/empty
        if not dependent_services:
            from app.reliability.correlator import SYSTEM_DEPENDENCY_EDGES
            downstreams = SYSTEM_DEPENDENCY_EDGES.get(subsystem, [])
            dependent_services.update(downstreams)

        return {
            "subsystem": component,
            "systemic_impact_score": round(systemic_score, 3),
            "severity": severity.value,
            "affected_subsystems": sorted(list(dependent_services)),
            "affected_workflows": active_workflows,
            "affected_tasks": active_tasks,
            "affected_tools": active_tools,
            "affected_resources": active_resources,
            "active_executions": active_executions,
            "second_order_cascades": second_order_cascades,
            "requires_precautionary_containment": severity in (FailureSeverity.P0, FailureSeverity.P1),
        }
