"""Alternative Hypothesis & Differentiation Engine for Task 112:
Generates competing causal explanations and formulates discriminating observations.

Strict Invariants:
- ALTERNATIVE HYPOTHESES CANNOT BE COLLAPSED INTO TRUTH
- EVERY ALTERNATIVE MUST PROVIDE A DISCRIMINATING OBSERVATION
- MULTIPLE HYPOTHESES MUST REMAIN COMPETING UNTIL EMPIRICALLY DISTINGUISHED
"""

from __future__ import annotations

from typing import List, Optional

from app.causal.explanation.domain import (
    CausalAlternative,
    CausalStatus,
    RootCauseCategory,
    gen_explanation_id,
)


class AlternativeEngine:
    """Generates competing causal alternatives and identifies discriminating observations."""

    @classmethod
    def generate_alternatives(
        cls,
        target_entity: str,
        primary_category: RootCauseCategory,
        primary_cause: Optional[str] = None,
    ) -> List[CausalAlternative]:
        """Synthesizes plausible alternative hypotheses based on incident context."""
        alternatives: List[CausalAlternative] = []

        # If primary is Resource Limit, plausible alternatives are Network Degradation and External Spike
        if primary_category == RootCauseCategory.RESOURCE_LIMIT:
            alternatives.append(
                CausalAlternative(
                    name="External Network Degradation",
                    hypothesis_summary="Packet loss or external gateway saturation caused timeouts rather than local memory exhaustion.",
                    proposed_cause="External network route latency or egress throttle",
                    confidence=0.45,
                    supporting_points=["Timeouts observed on outbound network calls", "Latency metrics escalated across all connections"],
                    contradicting_points=["Local memory pressure metric was at 98%"],
                    missing_evidence=["Network gateway interface packet drop counters"],
                    discriminating_observation="Inspect TCP retransmit rate and gateway egress drops; if drops < 0.1%, local resource exhaustion is confirmed.",
                    status=CausalStatus.POSSIBLE,
                )
            )
            alternatives.append(
                CausalAlternative(
                    name="Internal Deadlock / Contention",
                    hypothesis_summary="Database row-level lock contention stalled workers regardless of CPU/memory capacity.",
                    proposed_cause="Database transaction locking or thread starvation",
                    confidence=0.35,
                    supporting_points=["Worker thread utilization was elevated"],
                    contradicting_points=["Memory exhaustion alerts fired before lock acquisition delays"],
                    missing_evidence=["PostgreSQL lock wait duration telemetry"],
                    discriminating_observation="Check pg_stat_activity lock wait durations; lock wait > 5s indicates contention, whereas 0s confirms resource limit.",
                    status=CausalStatus.POSSIBLE,
                )
            )

        elif primary_category == RootCauseCategory.CAPABILITY_FAILURE:
            alternatives.append(
                CausalAlternative(
                    name="Configuration Drift / Invalid Secret",
                    hypothesis_summary="Service capability failed due to recent credential expiration or environment variable misconfiguration.",
                    proposed_cause="Expired API token or rotated encryption key",
                    confidence=0.4,
                    supporting_points=["Service capability threw authentication errors"],
                    contradicting_points=["Health checks showed graceful degradation rather than instant 401"],
                    missing_evidence=["Auth token expiration timestamp audit"],
                    discriminating_observation="Verify OAuth token validity timestamp; if valid, capability degradation was internal rather than credential-induced.",
                    status=CausalStatus.POSSIBLE,
                )
            )
            alternatives.append(
                CausalAlternative(
                    name="Upstream Provider Outage",
                    hypothesis_summary="The external provider hosted endpoint was down, making local capability appear degraded.",
                    proposed_cause="Third-party cloud service regional outage",
                    confidence=0.35,
                    supporting_points=["External API response codes returned 503"],
                    contradicting_points=["Other services using same provider reported nominal health"],
                    missing_evidence=["Public status dashboard logs from external provider"],
                    discriminating_observation="Compare failure rates of isolated endpoints on same provider across different workspaces.",
                    status=CausalStatus.POSSIBLE,
                )
            )

        elif primary_category == RootCauseCategory.DEPENDENCY_FAILURE:
            alternatives.append(
                CausalAlternative(
                    name="Local Network Partition",
                    hypothesis_summary="Local host network dropped connection to dependency rather than dependency itself failing.",
                    proposed_cause="Local interface routing failure or DNS resolution failure",
                    confidence=0.4,
                    supporting_points=["Connection reset errors in application log"],
                    contradicting_points=["DNS resolution for other hosts succeeded"],
                    missing_evidence=["Host network namespace routing table at incident time"],
                    discriminating_observation="Inspect host socket timeout telemetry; socket ECONNREFUSED indicates dependency failure, whereas EHOSTUNREACH indicates network partition.",
                    status=CausalStatus.POSSIBLE,
                )
            )

        else:
            # Generic competing hypothesis for Unknown or Contributing Factor
            alternatives.append(
                CausalAlternative(
                    name="Uninstrumented External Environmental Change",
                    hypothesis_summary="An unmonitored host process or external VM hypervisor contention caused the disruption.",
                    proposed_cause="Hypervisor CPU steal or unmonitored host daemon",
                    confidence=0.3,
                    supporting_points=["No internal Kairo error preceded the disruption"],
                    contradicting_points=["No hardware host telemetry is currently configured"],
                    missing_evidence=["Host OS dmesg and hypervisor steal metrics"],
                    discriminating_observation="Review hypervisor CPU steal metrics and OS system event log for unaccounted resource spikes.",
                    status=CausalStatus.UNKNOWN,
                )
            )

        return alternatives
