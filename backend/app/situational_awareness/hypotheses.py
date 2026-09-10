"""Causal hypothesis synthesis, candidate ranking, and diagnostic recommendations (Task 60)."""

from __future__ import annotations

import logging
import uuid

from app.situational_awareness.schemas import (
    CausalConfidence,
    CausalHypothesis,
    NormalizedEvent,
)

logger = logging.getLogger(__name__)


class HypothesisEngine:
    """Synthesizes plausible causal explanations, evaluates evidence, and recommends safe diagnostics."""

    def generate_hypotheses(
        self,
        situation_id: str,
        events: list[NormalizedEvent],
        affected_resources: list[str],
    ) -> list[CausalHypothesis]:
        """Generate ranked candidate causal explanations from correlated events."""
        if not events:
            return [
                CausalHypothesis(
                    hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                    situation_id=situation_id,
                    candidate_cause="ROOT_CAUSE_UNKNOWN",
                    confidence_level=CausalConfidence.UNKNOWN,
                    evidence_summary="Insufficient telemetry observations to form hypotheses.",
                    recommended_diagnostics=[
                        "Enable verbose diagnostic tracing",
                        "Inspect node health metrics",
                    ],
                )
            ]

        hypotheses: list[CausalHypothesis] = []

        # 1. Check for deployment events preceding symptoms
        deployment_events = [e for e in events if "deploy" in e.event_type.lower()]
        if deployment_events:
            dep_evt = deployment_events[0]
            hypotheses.append(
                CausalHypothesis(
                    hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                    situation_id=situation_id,
                    candidate_cause=f"Recent deployment '{dep_evt.subject}' on '{dep_evt.resource or 'cluster'}'",
                    confidence_level=CausalConfidence.SUPPORTED,
                    evidence_summary=f"Deployment occurred at {dep_evt.occurred_at.isoformat()}, immediately preceding incident signals.",
                    recommended_diagnostics=[
                        "Inspect recent commit diff and container image digest",
                        "Compare pre- and post-deployment error rates",
                        "Evaluate rollback feasibility",
                    ],
                )
            )

        # 2. Check for database / storage events
        db_events = [e for e in events if "database" in e.event_type.lower() or "sql" in e.event_type.lower()]
        if db_events:
            hypotheses.append(
                CausalHypothesis(
                    hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                    situation_id=situation_id,
                    candidate_cause="Database query lock contention or connection pool exhaustion",
                    confidence_level=CausalConfidence.LIKELY,
                    evidence_summary=f"Observed {len(db_events)} database error/latency events.",
                    recommended_diagnostics=[
                        "Check active pg_stat_activity connection counts",
                        "Analyze long-running SQL queries",
                        "Verify replica lag",
                    ],
                )
            )

        # 3. Check for high resource utilization
        metric_anomalies = [
            e
            for e in events
            if e.is_anomaly or "cpu" in e.event_type.lower() or "memory" in e.event_type.lower()
        ]
        if metric_anomalies:
            hypotheses.append(
                CausalHypothesis(
                    hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                    situation_id=situation_id,
                    candidate_cause="Sustained compute/memory resource saturation",
                    confidence_level=CausalConfidence.SUPPORTED,
                    evidence_summary=f"Detected {len(metric_anomalies)} metric anomaly events exceeding baseline thresholds.",
                    recommended_diagnostics=[
                        "Inspect top CPU consuming processes",
                        "Review memory heap dumps and GC pauses",
                        "Evaluate auto-scaling policy trigger",
                    ],
                )
            )

        # If no specific patterns matched, provide UNKNOWN root cause hypothesis
        if not hypotheses:
            hypotheses.append(
                CausalHypothesis(
                    hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                    situation_id=situation_id,
                    candidate_cause="Unclassified anomalous operational fluctuation",
                    confidence_level=CausalConfidence.SPECULATIVE,
                    evidence_summary="Circumstantial anomaly signals observed without clear causal anchor.",
                    recommended_diagnostics=["Inspect system logs and error stack traces"],
                )
            )

        logger.info("HYPOTHESES_GENERATED: situation=%s count=%d", situation_id, len(hypotheses))
        return hypotheses


hypothesis_engine = HypothesisEngine()
