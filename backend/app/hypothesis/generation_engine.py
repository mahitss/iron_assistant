"""Autonomous Hypothesis Generation Engine (Task 115 Section 10, 11, 12, 42).

Generates competing candidate explanations from causal models, temporal changes,
telemetry incidents, agent proposals, and user input.

Hard Invariants:
- UNKNOWN / OTHER CAUSE is ALWAYS included in every hypothesis set to prevent forced closure.
- Hypotheses are labeled with exact provenance: GENERATED, OBSERVED, USER_PROVIDED, AGENT_PROVIDED, MODEL_DERIVED, HISTORICAL, SIMULATED.
- Every meaningful hypothesis defines explicit testable falsification conditions.
- Hypotheses do NOT claim truth, belief, authorization, or action.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.hypothesis.domain import (
    Hypothesis,
    HypothesisClaim,
    HypothesisConfidenceProfile,
    HypothesisFalsificationCondition,
    HypothesisPrediction,
    HypothesisProvenance,
    HypothesisScope,
    HypothesisSet,
    HypothesisStatus,
)

logger = logging.getLogger("kairo.hypothesis.generation")


class HypothesisGenerationEngine:
    """Orchestrates creation of balanced, competing hypothesis sets."""

    def __init__(self, causal_service: Any = None, observation_service: Any = None) -> None:
        self.causal_service = causal_service
        self.observation_service = observation_service

    def create_hypothesis_set_for_target(
        self,
        target_description: str,
        scope: Optional[HypothesisScope] = None,
        target_incident_id: Optional[str] = None,
        candidate_explanations: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[HypothesisSet, List[Hypothesis]]:
        """Creates a balanced hypothesis set for an incident target, including competing causes and UNKNOWN."""
        effective_scope = scope or HypothesisScope(
            subsystems=["api", "database", "network", "worker"],
            time_window_start=datetime.now(timezone.utc),
        )

        hset = HypothesisSet(
            target_description=target_description,
            target_incident_id=target_incident_id,
            scope=effective_scope,
        )

        hypotheses: List[Hypothesis] = []

        if candidate_explanations:
            for item in candidate_explanations:
                hyp = self.build_hypothesis_from_dict(hset.set_id, item, effective_scope)
                hypotheses.append(hyp)
        else:
            # Generate archetypal competing hypotheses for incident target
            hypotheses.extend(self._generate_default_competing_hypotheses(hset.set_id, target_description, effective_scope))

        # MANDATORY INVARIANT: Always include the UNKNOWN / OTHER CAUSE hypothesis
        unknown_hyp = self._create_unknown_hypothesis(hset.set_id, effective_scope)
        hypotheses.append(unknown_hyp)

        hset.active_hypothesis_ids = [h.hypothesis_id for h in hypotheses if not h.is_unknown_hypothesis]
        hset.unknown_hypothesis_id = unknown_hyp.hypothesis_id

        logger.info(
            "Created hypothesis set %s with %d active hypotheses + 1 UNKNOWN hypothesis for target: %s",
            hset.set_id,
            len(hset.active_hypothesis_ids),
            target_description,
        )

        return hset, hypotheses

    def _generate_default_competing_hypotheses(
        self, set_id: str, target: str, scope: HypothesisScope
    ) -> List[Hypothesis]:
        h1 = Hypothesis(
            set_id=set_id,
            statement="Resource exhaustion (CPU/Memory saturation) caused the performance degradation or failure.",
            claim=HypothesisClaim(
                subject="system_resources",
                predicate="exhausted",
                object_value="saturation_exceeded",
                target_metric="cpu_memory_utilization",
                expected_direction="increase",
            ),
            scope=scope,
            status=HypothesisStatus.UNDER_INVESTIGATION,
            provenance=HypothesisProvenance.MODEL_DERIVED,
            mechanism_summary="High concurrency or worker memory leak led to CPU throttling and OOM worker crashes.",
            causal_node_refs=["worker_pool", "memory_usage", "cpu_throttling"],
            assumptions=["Worker processes were running high load", "Memory allocator limits reached"],
            falsification_conditions=[
                HypothesisFalsificationCondition(
                    description="Worker CPU and memory utilization remained below 50% throughout the incident window.",
                    required_observations=["telemetry.cpu_utilization", "telemetry.memory_usage"],
                    metric_thresholds={"cpu_max": 0.50, "memory_max": 0.50},
                    contradiction_signals=["worker_idle_metric"],
                )
            ],
            predictions=[
                HypothesisPrediction(
                    predicted_event="Worker process restarts or OOM killed logs in system journals",
                    expected_metric="oom_kill_count",
                    expected_value_range=(1.0, 100.0),
                    expected_timing_seconds=60.0,
                )
            ],
            confidence_profile=HypothesisConfidenceProfile(
                mechanism_plausibility=0.8,
                uncertainty=0.6,
                completeness=0.7,
            ),
        )

        h2 = Hypothesis(
            set_id=set_id,
            statement="Network degradation or packet loss caused connectivity drops and timeout cascades.",
            claim=HypothesisClaim(
                subject="network_fabric",
                predicate="degraded",
                object_value="packet_loss_or_high_rtt",
                target_metric="network_rtt_loss",
                expected_direction="increase",
            ),
            scope=scope,
            status=HypothesisStatus.UNDER_INVESTIGATION,
            provenance=HypothesisProvenance.MODEL_DERIVED,
            mechanism_summary="Upstream router congestion or link flapping caused TCP connection retransmissions and client timeouts.",
            causal_node_refs=["network_interface", "tcp_retransmits", "connection_pool"],
            assumptions=["Network path traversed degraded intermediate hops"],
            falsification_conditions=[
                HypothesisFalsificationCondition(
                    description="Network round-trip latency remained normal (<2ms) and packet loss was 0% across all nodes.",
                    required_observations=["telemetry.network_rtt", "telemetry.packet_loss"],
                    metric_thresholds={"rtt_ms": 2.0, "loss_pct": 0.0},
                    contradiction_signals=["zero_tcp_retransmit_signal"],
                )
            ],
            predictions=[
                HypothesisPrediction(
                    predicted_event="Spike in TCP SYN/ACK retransmissions and dropped packets",
                    expected_metric="tcp_retrans_count",
                    expected_value_range=(10.0, 1000.0),
                    expected_timing_seconds=30.0,
                )
            ],
            confidence_profile=HypothesisConfidenceProfile(
                mechanism_plausibility=0.75,
                uncertainty=0.65,
                completeness=0.65,
            ),
        )

        h3 = Hypothesis(
            set_id=set_id,
            statement="Downstream database or storage lock contention caused query queue buildup.",
            claim=HypothesisClaim(
                subject="database_subsystem",
                predicate="contended",
                object_value="lock_contention",
                target_metric="db_query_duration",
                expected_direction="increase",
            ),
            scope=scope,
            status=HypothesisStatus.UNDER_INVESTIGATION,
            provenance=HypothesisProvenance.MODEL_DERIVED,
            mechanism_summary="Long-running transactional migration or table locks stalled API request threads.",
            causal_node_refs=["db_connection_pool", "active_transactions", "lock_wait_time"],
            assumptions=["Database queries blocked waiting on shared locks"],
            falsification_conditions=[
                HypothesisFalsificationCondition(
                    description="Database active lock wait times were 0ms and transaction duration remained nominal (<5ms).",
                    required_observations=["telemetry.db_lock_wait_ms", "telemetry.db_query_p99"],
                    metric_thresholds={"lock_wait_ms": 0.0, "query_p99_ms": 5.0},
                    contradiction_signals=["db_health_green"],
                )
            ],
            predictions=[
                HypothesisPrediction(
                    predicted_event="Elevated lock wait duration in database engine metrics",
                    expected_metric="lock_wait_time_ms",
                    expected_value_range=(500.0, 30000.0),
                    expected_timing_seconds=45.0,
                )
            ],
            confidence_profile=HypothesisConfidenceProfile(
                mechanism_plausibility=0.7,
                uncertainty=0.7,
                completeness=0.6,
            ),
        )

        return [h1, h2, h3]

    def _create_unknown_hypothesis(self, set_id: str, scope: HypothesisScope) -> Hypothesis:
        """Explicit UNKNOWN / OTHER CAUSE hypothesis."""
        return Hypothesis(
            set_id=set_id,
            statement="Unknown or unobserved external factor caused the incident (CAUSE_UNKNOWN).",
            claim=HypothesisClaim(
                subject="environment",
                predicate="unaccounted_anomaly",
                object_value="unknown_factor",
                target_metric="unknown",
            ),
            scope=scope,
            status=HypothesisStatus.UNKNOWN,
            provenance=HypothesisProvenance.GENERATED,
            is_unknown_hypothesis=True,
            mechanism_summary="Unobserved root cause not covered by current known system instrumentation.",
            assumptions=["Instrumented telemetry may have blind spots"],
            falsification_conditions=[
                HypothesisFalsificationCondition(
                    description="Another competing hypothesis is verified with rigorous independent evidence and zero contradictions.",
                    required_observations=["competing_hypothesis_verified"],
                )
            ],
            confidence_profile=HypothesisConfidenceProfile(
                uncertainty=1.0,
                completeness=0.2,
                evidence_strength=0.0,
            ),
        )

    def build_hypothesis_from_dict(
        self, set_id: str, data: Dict[str, Any], scope: HypothesisScope
    ) -> Hypothesis:
        """Parses user or agent submitted hypothesis data while strictly sanitizing authority claims."""
        statement = str(data.get("statement", "Candidate explanation")).strip()
        provenance_str = data.get("provenance", "AGENT_PROVIDED").upper()
        try:
            provenance = HypothesisProvenance(provenance_str)
        except ValueError:
            provenance = HypothesisProvenance.AGENT_PROVIDED

        proposer_agent_id = data.get("proposer_agent_id")
        claim_data = data.get("claim", {})
        claim = HypothesisClaim(
            subject=str(claim_data.get("subject", "system")),
            predicate=str(claim_data.get("predicate", "abnormal")),
            object_value=claim_data.get("object_value"),
            target_metric=claim_data.get("target_metric"),
            expected_direction=claim_data.get("expected_direction"),
        )

        fals_conditions: List[HypothesisFalsificationCondition] = []
        for fc in data.get("falsification_conditions", []):
            fals_conditions.append(
                HypothesisFalsificationCondition(
                    description=str(fc.get("description", "Observation disproves claim")),
                    required_observations=fc.get("required_observations", []),
                    metric_thresholds=fc.get("metric_thresholds", {}),
                    contradiction_signals=fc.get("contradiction_signals", []),
                )
            )

        predictions: List[HypothesisPrediction] = []
        for pr in data.get("predictions", []):
            predictions.append(
                HypothesisPrediction(
                    predicted_event=str(pr.get("predicted_event", "")),
                    predicted_state=pr.get("predicted_state", {}),
                    expected_metric=pr.get("expected_metric"),
                    expected_timing_seconds=float(pr.get("expected_timing_seconds", 0.0)),
                )
            )

        return Hypothesis(
            set_id=set_id,
            statement=statement,
            claim=claim,
            scope=scope,
            status=HypothesisStatus.UNDER_INVESTIGATION,
            provenance=provenance,
            proposer_agent_id=proposer_agent_id,
            mechanism_summary=str(data.get("mechanism_summary", "")),
            causal_node_refs=data.get("causal_node_refs", []),
            assumptions=data.get("assumptions", []),
            falsification_conditions=fals_conditions,
            predictions=predictions,
            confidence_profile=HypothesisConfidenceProfile(
                mechanism_plausibility=0.6,
                uncertainty=0.7,
                completeness=0.5,
            ),
        )
