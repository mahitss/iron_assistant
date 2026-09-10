"""Unified Causal Reasoning Service orchestrator (Task 55)."""

from __future__ import annotations

from typing import Any

from app.causal.alternatives import CausalAlternativeGenerator
from app.causal.counterfactuals import CounterfactualEngine
from app.causal.dependencies import CausalDependencyIntegrator
from app.causal.evaluation import CausalEvaluator
from app.causal.evidence import create_evidence
from app.causal.experiments import CausalExperimentEngine
from app.causal.explanations import CausalExplanationEngine
from app.causal.graph import CausalGraphEngine
from app.causal.hypotheses import CausalHypothesisManager
from app.causal.impact import CausalImpactEngine
from app.causal.interventions import InterventionEngine
from app.causal.nodes import create_node
from app.causal.observations import ObservationIngestor
from app.causal.root_cause import RootCauseAnalysisEngine
from app.causal.safety import CausalSafetyGuard
from app.causal.schemas import (
    CausalEdge,
    CausalEvidence,
    CausalExperiment,
    CausalExplanation,
    CausalGraph,
    CausalHypothesis,
    CausalNode,
    CausalRelationshipType,
    CausalScope,
    CounterfactualScenario,
    EvidenceStrength,
    EvidenceType,
    FallacyDetectionResult,
    Intervention,
    InterventionType,
    RootCauseAnalysis,
    RootCauseChain,
    RootCauseStatus,
)


class CausalService:
    """Singleton service providing full causal reasoning, root cause analysis, interventions, and explanations."""

    def __init__(self) -> None:
        self._graphs: dict[str, CausalGraph] = {}
        self._analyses: dict[str, RootCauseAnalysis] = {}
        self._interventions: dict[str, Intervention] = {}
        self._experiments: dict[str, CausalExperiment] = {}
        self._hypotheses: dict[str, CausalHypothesis] = {}
        self._scenarios: dict[str, CounterfactualScenario] = {}
        self._observations: list[dict[str, Any]] = []

        # Initialize default system graph
        default_graph = CausalGraphEngine.create_graph(graph_id="system_default", scope=CausalScope.SYSTEM)
        self._graphs["system_default"] = default_graph

    def get_graph(self, graph_id: str = "system_default") -> CausalGraph:
        """Retrieve a causal graph by ID."""
        if graph_id not in self._graphs:
            self._graphs[graph_id] = CausalGraphEngine.create_graph(graph_id=graph_id, scope=CausalScope.SYSTEM)
        return self._graphs[graph_id]

    def add_node(
        self,
        entity: str,
        variable: str,
        state: Any,
        source: str = "telemetry",
        confidence: float = 1.0,
        graph_id: str = "system_default",
    ) -> CausalNode:
        """Add or update a causal node."""
        node = create_node(entity=entity, variable=variable, state=state, source=source, confidence=confidence)
        graph = self.get_graph(graph_id)
        graph.nodes[node.node_id] = node
        graph.version += 1
        return node

    def add_edge(
        self,
        cause: str,
        effect: str,
        relationship: CausalRelationshipType = CausalRelationshipType.CAUSES,
        confidence: float = 0.5,
        evidence: list[CausalEvidence] | None = None,
        graph_id: str = "system_default",
    ) -> CausalEdge:
        """Prompt #6, #8, #19, #26: Add a causal edge with evidence validation."""
        ev_list = evidence or []
        CausalSafetyGuard.validate_causal_claim(relationship=relationship, evidence_list=ev_list)

        graph = self.get_graph(graph_id)
        edge_id = f"{cause}->{effect}"
        edge = CausalEdge(
            edge_id=edge_id,
            cause=cause,
            effect=effect,
            relationship=relationship,
            confidence=confidence,
            evidence_refs=[ev.evidence_id for ev in ev_list],
            status="ACTIVE" if confidence >= 0.7 else "CANDIDATE",
        )
        graph.edges[edge_id] = edge
        graph.version += 1
        return edge

    def record_observation(
        self,
        entity: str,
        variable: str,
        value: Any,
        source: str = "telemetry",
    ) -> dict[str, Any]:
        """Ingest raw observation."""
        obs = ObservationIngestor.ingest_observation(entity=entity, variable=variable, value=value, source=source)
        self._observations.append(obs)
        return obs

    def analyze_root_cause(
        self,
        incident_id: str,
        symptom: str,
        observations: list[dict[str, Any]] | None = None,
        telemetry_metrics: dict[str, float] | None = None,
        service_dependencies: dict[str, list[str]] | None = None,
        graph_id: str = "system_default",
    ) -> RootCauseAnalysis:
        """Full root-cause analysis distinguishing correlation, dependency, and causation."""
        self.get_graph(graph_id)
        deps = service_dependencies or {
            "api_gateway": ["auth_service", "database_cluster"],
            "auth_service": ["redis_cache"],
        }

        # 1. Generate canonical alternative hypotheses
        alternatives = CausalAlternativeGenerator.generate_candidates(incident_type="service_latency_increase")

        # 2. Collect evidence from observations and telemetry
        evidence_list: list[CausalEvidence] = []

        if telemetry_metrics:
            for k, val in telemetry_metrics.items():
                ev_str = EvidenceStrength.STRONG if "error" in k or "latency" in k else EvidenceStrength.MODERATE
                ev = create_evidence(
                    evidence_type=EvidenceType.TELEMETRY,
                    source=f"metric:{k}",
                    observation={"metric": k, "value": val},
                    strength=ev_str,
                    independence=0.9,
                )
                evidence_list.append(ev)

        # 3. Create analysis object
        analysis = RootCauseAnalysisEngine.create_analysis(
            incident_id=incident_id,
            symptom=symptom,
            candidate_causes=alternatives,
            evidence=evidence_list,
        )

        # 4. Integrate topology candidates without conflating with direct cause
        CausalDependencyIntegrator.extract_candidates_from_digital_twin(
            service_graph=deps,
            active_incident_service="api_gateway",
        )

        # 5. Evaluate hypotheses
        hypotheses = []
        for cand in alternatives:
            cand_tokens = [tok for tok in cand.lower().split('_') if len(tok) > 3]
            matched_evidence = [
                ev for ev in evidence_list
                if cand.lower() in str(ev.observation).lower()
                or (cand_tokens and all(tok in str(ev.observation).lower() for tok in cand_tokens))
            ]
            hyp = CausalHypothesisManager.create_hypothesis(
                cause=cand,
                effect=symptom,
                mechanism=f"Propagation through architectural dependency {cand} -> {symptom}",
                evidence=matched_evidence,
                alternatives=[a for a in alternatives if a != cand],
            )
            hypotheses.append(hyp)
            self._hypotheses[hyp.hypothesis_id] = hyp

        # 6. Rank and identify root cause and contributing factors
        ranked = sorted(hypotheses, key=lambda h: len(h.evidence), reverse=True)
        primary = ranked[0] if ranked and ranked[0].evidence else None

        if primary and primary.evidence:
            has_critical = any(ev.strength.value in ("STRONG", "CRITICAL") for ev in primary.evidence)
            status = RootCauseStatus.LIKELY if has_critical else RootCauseStatus.SUPPORTED
            analysis.root_cause = primary.cause
            analysis.status = status
            analysis.confidence = 0.75 if has_critical else 0.55
            analysis.contributing_factors = [h.cause for h in ranked[1:3] if h.evidence]
            analysis.surviving_causes = [primary.cause] + analysis.contributing_factors
            analysis.eliminated_causes = [
                {"cause": h.cause, "reason": "No correlated telemetry or trace evidence observed."}
                for h in ranked[3:]
            ]
        else:
            # Prompt #163, #164: Never force a root cause without evidence
            analysis.status = RootCauseStatus.UNKNOWN
            analysis.root_cause = None
            analysis.confidence = 0.2
            analysis.surviving_causes = alternatives

        # Build causal chain
        analysis.causal_chain = RootCauseChain(
            underlying_condition="high_load_saturation",
            trigger=analysis.root_cause or "unidentified_trigger",
            mechanism="thread_pool_exhaustion",
            intermediate_state="elevated_queue_depth",
            symptom=symptom,
            impact="Degraded service level objective (SLO)",
        )

        self._analyses[incident_id] = analysis
        return analysis

    def explain_incident(self, incident_id: str) -> CausalExplanation:
        """Generate a complete 6-part causal explanation."""
        analysis = self._analyses.get(incident_id)
        if not analysis:
            analysis = self.analyze_root_cause(incident_id=incident_id, symptom="Unspecified failure")

        why_text = (
            f"The primary likely cause was '{analysis.root_cause}', with contributing factor(s): {analysis.contributing_factors}."
            if analysis.root_cause
            else "Investigation indicates the root cause remains UNKNOWN due to insufficient telemetry."
        )

        evidence_summaries = [
            f"{ev.type.value} ({ev.source}): {ev.observation.get('metric', 'obs')} = {ev.observation.get('value', 'detected')}"
            for ev in analysis.evidence
        ]

        return CausalExplanationEngine.generate_explanation(
            incident_name=incident_id,
            what_happened=f"Incident {incident_id}: Symptom observed.",
            why_it_happened=why_text,
            evidence_list=evidence_summaries,
            alternatives=[e.get("cause", "") for e in analysis.eliminated_causes],
            uncertainty=(
                "Assessed as LIKELY based on observational telemetry; requires controlled rollback or canary test to achieve VERIFIED status."
                if analysis.status != RootCauseStatus.VERIFIED
                else "Empirically verified via intervention test."
            ),
            test_plan=[
                "Deploy configuration canary with 5% traffic",
                "Monitor database connection pool metrics for 5 minutes",
                "Execute controlled rollback if error rate exceeds 2%",
            ],
            confidence_label=analysis.status.value,
            is_verified=analysis.status == RootCauseStatus.VERIFIED,
        )

    def ask_question(self, incident_id: str, question: str) -> dict[str, Any]:
        """Answer natural language causal inquiries."""
        analysis = self._analyses.get(incident_id)
        if not analysis:
            analysis = self.analyze_root_cause(incident_id=incident_id, symptom="Investigated symptom")
        return CausalExplanationEngine.answer_user_question(question=question, analysis=analysis)

    def propose_intervention(
        self,
        target: str,
        change: dict[str, Any],
        expected_effect: dict[str, Any],
        intervention_type: InterventionType = InterventionType.CONFIG_CHANGE,
        risk: str = "MEDIUM",
        is_production: bool = False,
        approved_by: str | None = None,
    ) -> Intervention:
        """Propose an authorized intervention to test a causal hypothesis."""
        intv = InterventionEngine.create_intervention(
            target=target,
            change=change,
            expected_effect=expected_effect,
            intervention_type=intervention_type,
            risk=risk,
        )
        if approved_by or not is_production:
            InterventionEngine.validate_and_authorize(
                intervention=intv,
                is_production=is_production,
                approved_by=approved_by,
            )
        self._interventions[intv.intervention_id] = intv
        return intv

    def evaluate_intervention(
        self,
        intervention_id: str,
        actual_effect: dict[str, Any],
        hypothesis_id: str | None = None,
    ) -> tuple[Intervention, CausalEvidence, bool]:
        """Evaluate outcome of an intervention."""
        intv = self._interventions.get(intervention_id)
        if not intv:
            raise KeyError(f"Intervention '{intervention_id}' not found.")

        hyp = self._hypotheses.get(hypothesis_id) if hypothesis_id else None
        updated_intv, evidence, matched = InterventionEngine.evaluate_intervention_result(
            intervention=intv,
            actual_effect=actual_effect,
            hypothesis=hyp,
        )

        return updated_intv, evidence, matched

    def evaluate_counterfactual(
        self,
        removed_cause: str,
        baseline_state: dict[str, Any],
        graph_id: str = "system_default",
    ) -> CounterfactualScenario:
        """Prompt #63, #64, #65: Evaluate what would have happened if X had not occurred."""
        graph = self.get_graph(graph_id)
        scenario = CounterfactualEngine.evaluate_what_if(
            question=f"What would have happened if {removed_cause} had not occurred?",
            removed_cause=removed_cause,
            baseline_state=baseline_state,
            causal_graph=graph,
        )
        self._scenarios[scenario.scenario_id] = scenario
        return scenario

    def create_experiment(
        self,
        hypothesis_id: str,
        treatment: dict[str, Any],
        control: dict[str, Any],
        metric: str,
        duration_seconds: int = 300,
        is_high_risk: bool = False,
        approved_by: str | None = None,
    ) -> CausalExperiment:
        """Create and optionally authorize an A/B causal experiment."""
        auth = {"approved": bool(approved_by), "approved_by": approved_by}
        exp = CausalExperimentEngine.create_experiment(
            hypothesis_id=hypothesis_id,
            treatment=treatment,
            control=control,
            metric=metric,
            duration_seconds=duration_seconds,
            authorization=auth,
            is_high_risk=is_high_risk,
        )
        self._experiments[exp.experiment_id] = exp
        return exp

    def detect_fallacies(
        self,
        cause: str,
        effect: str,
        evidence: list[CausalEvidence] | None = None,
        graph_id: str = "system_default",
        temporal_only: bool = False,
    ) -> FallacyDetectionResult:
        """Audit for post hoc, confounding, reverse causality, and collider fallacies."""
        graph = self.get_graph(graph_id)
        return CausalEvaluator.detect_fallacies(
            cause=cause,
            effect=effect,
            evidence=evidence or [],
            graph=graph,
            temporal_only=temporal_only,
        )

    def get_blast_radius(
        self,
        origin_service: str,
        service_graph: dict[str, list[str]] | None = None,
        graph_id: str = "system_default",
    ) -> dict[str, Any]:
        """Calculate blast radius distinguishing topology reachability from causation."""
        graph = self.get_graph(graph_id)
        sg = service_graph or {
            "api_gateway": ["auth_service", "database_cluster"],
            "auth_service": ["redis_cache"],
            "database_cluster": [],
            "redis_cache": [],
        }
        return CausalImpactEngine.calculate_blast_radius(
            origin_service=origin_service,
            service_graph=sg,
            causal_graph=graph,
        )


# Global singleton instance
causal_service = CausalService()
