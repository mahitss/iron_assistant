"""Root Cause & Contributor Analysis Engine for Task 112:
Dissects complex incidents into triggers, contributors, enabling conditions, and upstream causes.

Strict Invariants:
- NO FORCED MONO-CAUSALITY (Supports multiple contributors & unknown causes)
- CONTRIBUTION != SOLE CAUSE
- UNVERIFIED HYPOTHESIS != FACT
- CORRELATION != CAUSATION
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.causal.explanation.domain import (
    CausalConfidenceBreakdown,
    CausalContributor,
    CausalLink,
    CausalRelationshipRole,
    CausalStatus,
    EventChain,
    EvidenceClassification,
    ExplanationEvidence,
    ExplanationGap,
    RootCauseCategory,
    gen_explanation_id,
    utc_now,
)
from app.causal.temporal_engine import TemporalCausalityEngine


class RootCauseEngine:
    """Dissects failures and state changes into multi-faceted causal contributor graphs."""

    @classmethod
    def analyze_causes(
        cls,
        target_entity: str,
        target_symptom: str,
        event_chain: EventChain,
        telemetry_evidence: Optional[List[ExplanationEvidence]] = None,
        causal_graph_edges: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[
        RootCauseCategory,
        Optional[str],
        Optional[str],
        List[CausalLink],
        List[CausalContributor],
        List[ExplanationGap],
    ]:
        """Analyzes event chain and evidence to identify root triggers, contributors, and gaps."""
        evidence = telemetry_evidence or []
        links: List[CausalLink] = []
        contributors: List[CausalContributor] = []
        gaps: List[ExplanationGap] = []

        if not event_chain.steps and not evidence:
            # Case: Zero empirical evidence available
            gaps.append(
                ExplanationGap(
                    subsystem=target_entity,
                    description=f"Zero telemetry or event transitions recorded preceding symptom '{target_symptom}'",
                    why_it_matters="Cannot infer causal mechanisms without empirical observations",
                    missing_data_type="telemetry",
                    severity="HIGH",
                )
            )
            return (
                RootCauseCategory.UNKNOWN,
                None,
                None,
                [],
                [],
                gaps,
            )

        # Inspect event steps for known trigger and failure patterns
        detected_category = RootCauseCategory.UNKNOWN
        primary_cause: Optional[str] = None
        primary_mechanism: Optional[str] = None

        # Check for Resource Exhaustion pattern (Resource Pressure -> Queue -> Latency -> Failure)
        resource_steps = [s for s in event_chain.steps if "resource" in s.event_type.lower() or "memory" in s.event_type.lower() or "cpu" in s.event_type.lower()]
        timeout_steps = [s for s in event_chain.steps if "timeout" in s.event_type.lower() or "latency" in s.event_type.lower()]
        capability_steps = [s for s in event_chain.steps if "degraded" in str(s.state_after).lower() or "capability" in s.event_type.lower()]
        dependency_steps = [s for s in event_chain.steps if "dependency" in s.event_type.lower() or "external" in s.event_type.lower()]

        if resource_steps and timeout_steps:
            detected_category = RootCauseCategory.RESOURCE_LIMIT
            primary_cause = f"Resource exhaustion on {resource_steps[0].entity_id}"
            primary_mechanism = "Resource starvation caused queue saturation leading to downstream operation timeout."

            # Construct causal link
            link = CausalLink(
                source_node=resource_steps[0].entity_id,
                target_node=timeout_steps[0].entity_id,
                relationship_role=CausalRelationshipRole.DIRECT_CAUSE,
                status=CausalStatus.SUPPORTED,
                mechanism=primary_mechanism,
                lag_seconds=max(0.0, (timeout_steps[0].timestamp - resource_steps[0].timestamp).total_seconds()),
                confidence=CausalConfidenceBreakdown.calculate_composite(
                    temporal_fit=1.0,
                    mechanism_fit=0.9,
                    evidence_strength=0.85,
                    observational_completeness=0.8,
                ),
                is_temporally_valid=True,
            )
            links.append(link)

            contributors.append(
                CausalContributor(
                    entity_id=resource_steps[0].entity_id,
                    category=RootCauseCategory.RESOURCE_LIMIT,
                    role=CausalRelationshipRole.TRIGGER,
                    description="Memory/CPU threshold exceeded",
                    qualitative_contribution="HIGH",
                    estimated_fraction=0.6,
                    confidence=0.85,
                )
            )
            contributors.append(
                CausalContributor(
                    entity_id=timeout_steps[0].entity_id,
                    category=RootCauseCategory.CONTRIBUTING_FACTOR,
                    role=CausalRelationshipRole.MEDIATOR,
                    description="Request queue backlog overflow",
                    qualitative_contribution="MODERATE",
                    estimated_fraction=0.3,
                    confidence=0.8,
                )
            )

        elif capability_steps:
            detected_category = RootCauseCategory.CAPABILITY_FAILURE
            primary_cause = f"Degraded capability on {capability_steps[0].entity_id}"
            primary_mechanism = "Subsystem entered degraded operating mode, failing required service level."
            contributors.append(
                CausalContributor(
                    entity_id=capability_steps[0].entity_id,
                    category=RootCauseCategory.CAPABILITY_FAILURE,
                    role=CausalRelationshipRole.DIRECT_CAUSE,
                    description=f"Capability degradation on {capability_steps[0].entity_id}",
                    qualitative_contribution="HIGH",
                    estimated_fraction=0.7,
                    confidence=0.8,
                )
            )

        elif dependency_steps:
            detected_category = RootCauseCategory.DEPENDENCY_FAILURE
            primary_cause = f"Upstream dependency failure on {dependency_steps[0].entity_id}"
            primary_mechanism = "Third-party or external dependency failed to respond within SLA."
            contributors.append(
                CausalContributor(
                    entity_id=dependency_steps[0].entity_id,
                    category=RootCauseCategory.DEPENDENCY_FAILURE,
                    role=CausalRelationshipRole.UPSTREAM_CAUSE,
                    description="Upstream failure propagated across dependency boundary",
                    qualitative_contribution="HIGH",
                    estimated_fraction=0.8,
                    confidence=0.85,
                )
            )

        else:
            # Fallback: Check if there's any preceding event
            if event_chain.steps:
                detected_category = RootCauseCategory.CONTRIBUTING_FACTOR
                latest_step = event_chain.steps[-1]
                primary_cause = f"Preceding transition on {latest_step.entity_id} ({latest_step.event_type})"
                primary_mechanism = "Temporal succession observed; direct causal mechanism unverified."
                contributors.append(
                    CausalContributor(
                        entity_id=latest_step.entity_id,
                        category=RootCauseCategory.CONTRIBUTING_FACTOR,
                        role=CausalRelationshipRole.TEMPORALLY_ASSOCIATED,
                        description=f"Occurred {(event_chain.end_time - latest_step.timestamp).total_seconds():.1f}s before incident",
                        qualitative_contribution="UNCERTAIN",
                        confidence=0.4,
                    )
                )
                gaps.append(
                    ExplanationGap(
                        subsystem=target_entity,
                        description="Temporal correlation detected but missing definitive mechanistic trace",
                        why_it_matters="Cannot distinguish direct causation from coincident external trigger",
                        severity="MEDIUM",
                    )
                )
            else:
                detected_category = RootCauseCategory.UNKNOWN

        return detected_category, primary_cause, primary_mechanism, links, contributors, gaps
