"""Candidate Observation Generation and Prompt-Injection Defense Engine for Task 114.
Synthesizes bounded observation options across PASSIVE, ACTIVE, CONTROLLED, USER, and WAIT methods.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from app.observation.domain import (
    InformationGap,
    ObservationCandidate,
    ObservationCost,
    ObservationMethodType,
    ObservationRisk,
    ObservationScope,
    UncertaintyDimensionType,
)

logger = logging.getLogger("kairo.observation.candidate_generator")


class CandidateObservationGenerator:
    """Generates safe, structured observation candidates for identified information gaps (Section 11, 12, 18)."""

    _INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(previous|governance|security|all)", re.IGNORECASE),
        re.compile(r"system\s*:", re.IGNORECASE),
        re.compile(r"(reveal|dump|leak)\s+(secrets|tokens|keys|passwords)", re.IGNORECASE),
        re.compile(r"(disable|bypass)\s+(safeguards|emergency\s*stop)", re.IGNORECASE),
        re.compile(r"(rm\s+-rf|drop\s+database|truncate\s+table)", re.IGNORECASE),
    ]

    @classmethod
    def generate_candidates(
        cls,
        gap: InformationGap,
        available_sources: Optional[List[str]] = None,
        deadline_seconds: Optional[float] = None,
    ) -> List[ObservationCandidate]:
        candidates: List[ObservationCandidate] = []
        available_sources = available_sources or ["system_telemetry", "diagnostics_bus", "world_state_twin"]

        # If gap was already resolved internally, no new active candidates needed
        if gap.is_resolved_by_existing_data:
            return []

        # 1. PASSIVE: Ingest existing or upcoming telemetry / log events
        candidates.append(
            cls._build_candidate(
                gap=gap,
                name=f"Passive Telemetry Ingestion for {gap.affected_entity}",
                source="system_telemetry",
                method=ObservationMethodType.PASSIVE,
                cost=ObservationCost(compute_units=0.01, network_latency_ms=10.0),
                risk=ObservationRisk(security_risk_level="LOW"),
                payload={"target_entity": gap.affected_entity, "metric": gap.affected_state},
                deadline=deadline_seconds,
            )
        )

        # 2. ACTIVE: Targeted state inspection / health probe
        candidates.append(
            cls._build_candidate(
                gap=gap,
                name=f"Active State Query for {gap.affected_entity}:{gap.affected_state}",
                source="diagnostics_bus",
                method=ObservationMethodType.ACTIVE,
                cost=ObservationCost(compute_units=0.08, network_latency_ms=150.0),
                risk=ObservationRisk(security_risk_level="LOW"),
                payload={"target_entity": gap.affected_entity, "query": f"inspect_{gap.affected_state.lower()}"},
                deadline=deadline_seconds,
            )
        )

        # 3. USER: Intent Clarification if gap is related to INTENT (Section 19)
        if UncertaintyDimensionType.INTENT in gap.uncertainty_dimensions or "intent" in gap.affected_state.lower():
            candidates.append(
                cls._build_candidate(
                    gap=gap,
                    name="Targeted User Intent Clarification",
                    source="user_interface",
                    method=ObservationMethodType.USER,
                    cost=ObservationCost(compute_units=0.02, interruption_penalty=1.5),
                    risk=ObservationRisk(security_risk_level="LOW"),
                    payload={"question": gap.question, "urgency": "HIGH"},
                    deadline=deadline_seconds,
                )
            )

        # 4. CONTROLLED: If discriminating competing causal hypotheses (Section 22)
        if UncertaintyDimensionType.CAUSAL in gap.uncertainty_dimensions or "causal" in gap.affected_state.lower():
            candidates.append(
                cls._build_candidate(
                    gap=gap,
                    name=f"Controlled Sandboxed Replay for {gap.affected_entity}",
                    source="simulation_sandbox",
                    method=ObservationMethodType.CONTROLLED,
                    scope=ObservationScope.SIMULATION_ONLY,
                    cost=ObservationCost(compute_units=0.25, network_latency_ms=300.0),
                    risk=ObservationRisk(security_risk_level="LOW", reversibility="REVERSIBLE"),
                    payload={"experiment_type": "OBSERVATIONAL_REPLAY", "target": gap.affected_entity},
                    deadline=deadline_seconds,
                )
            )

        # 5. WAIT: If a natural state transition or delayed telemetry is anticipated (Section 17)
        candidates.append(
            cls._build_candidate(
                gap=gap,
                name=f"Wait for Imminent State Convergence on {gap.affected_entity}",
                source="temporal_bus",
                method=ObservationMethodType.WAIT,
                cost=ObservationCost(compute_units=0.0, network_latency_ms=0.0),
                risk=ObservationRisk(security_risk_level="LOW"),
                payload={"wait_seconds": min(5.0, gap.freshness_requirement_seconds / 2)},
                deadline=deadline_seconds,
            )
        )

        return candidates

    @classmethod
    def _build_candidate(
        cls,
        gap: InformationGap,
        name: str,
        source: str,
        method: ObservationMethodType,
        cost: ObservationCost,
        risk: ObservationRisk,
        payload: Dict[str, Any],
        scope: ObservationScope = ObservationScope.ENTITY,
        deadline: Optional[float] = None,
    ) -> ObservationCandidate:
        # Prompt-Injection Firewall: Sanitize payload and query strings
        sanitized_payload, has_injection = cls.sanitize_observation_data(payload)
        is_blocked = False
        block_reason = ""

        if has_injection:
            logger.warning(f"Prompt injection attempt intercepted in candidate '{name}'. Disarmed as raw DATA.")

        # Hard Rule: Observation cannot mutate production state (Section 38, 70)
        risk.state_mutation_risk = False

        return ObservationCandidate(
            gap_id=gap.gap_id,
            name=name,
            target_source=source,
            method=method,
            scope=scope,
            query_payload=sanitized_payload,
            cost=cost,
            risk=risk,
            expected_latency_seconds=max(0.1, cost.network_latency_ms / 1000.0),
            deadline_seconds=deadline,
            is_blocked=is_blocked,
            block_reason=block_reason,
            prompt_injection_sanitized=True,
        )

    @classmethod
    def sanitize_observation_data(cls, data: Any) -> tuple[Any, bool]:
        """Neutralizes any prompt injection or command string, treating it strictly as inert DATA (Section 35)."""
        has_injection = False
        if isinstance(data, str):
            for pattern in cls._INJECTION_PATTERNS:
                if pattern.search(data):
                    has_injection = True
                    # Disarm by escaping and marking as raw literal data
                    data = f"[DATA_ONLY: {pattern.sub('[DISARMED]', data)}]"
            return data, has_injection
        elif isinstance(data, dict):
            clean_dict = {}
            for k, v in data.items():
                clean_v, found = cls.sanitize_observation_data(v)
                if found:
                    has_injection = True
                clean_dict[k] = clean_v
            return clean_dict, has_injection
        elif isinstance(data, list):
            clean_list = []
            for item in data:
                clean_item, found = cls.sanitize_observation_data(item)
                if found:
                    has_injection = True
                clean_list.append(clean_item)
            return clean_list, has_injection
        return data, has_injection
