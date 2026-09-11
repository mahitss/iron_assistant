"""Resilience Gap Detector & Scorecard Engine (Task 76).

Detects 12 resilience gaps across system topologies and computes
interpretable multi-dimensional scorecards across 12 resilience dimensions.
"""

from datetime import UTC, datetime
from typing import Any

from app.resilience.defense_schemas import (
    RedundancyBackupMode,
    RedundancyType,
    ResilienceDimensionScore,
    ResilienceDimensionType,
    ResilienceGap,
    ResilienceGapType,
    ResilienceScorecard,
    generate_defense_id,
    utc_now,
)


class ResilienceGapDetector:
    """Detects systemic resilience weaknesses, single points of failure, missing redundancies,

    and evaluates multi-dimensional resilience scorecards.
    """

    def __init__(self) -> None:
        pass

    def evaluate_redundancy(self, entity_id: str, topology: dict[str, Any]) -> tuple[RedundancyType, list[RedundancyBackupMode]]:
        """Determines redundancy status and available backup modes for an entity.

        Never assumes unknown redundancy exists.
        """
        nodes = topology.get("nodes", {})
        node_meta = nodes.get(entity_id, {})
        backups = node_meta.get("backups", [])
        redundancy_declared = node_meta.get("has_redundancy")

        modes: list[RedundancyBackupMode] = []
        for b in backups:
            mode_str = b.get("mode", "").lower() if isinstance(b, dict) else str(b).lower()
            if "active" in mode_str:
                modes.append(RedundancyBackupMode.ACTIVE_BACKUP)
            elif "passive" in mode_str or "standby" in mode_str:
                modes.append(RedundancyBackupMode.PASSIVE_BACKUP)
            elif "service" in mode_str:
                modes.append(RedundancyBackupMode.ALTERNATIVE_SERVICE)
            elif "workflow" in mode_str:
                modes.append(RedundancyBackupMode.ALTERNATIVE_WORKFLOW)
            elif "manual" in mode_str:
                modes.append(RedundancyBackupMode.MANUAL_FALLBACK)
            elif "resource" in mode_str:
                modes.append(RedundancyBackupMode.SUBSTITUTE_RESOURCE)

        if len(modes) > 0 or redundancy_declared is True:
            return RedundancyType.KNOWN_REDUNDANCY, modes
        elif redundancy_declared is False:
            return RedundancyType.NO_REDUNDANCY, []
        else:
            return RedundancyType.REDUNDANCY_UNKNOWN, []

    def detect_gaps(self, topology: dict[str, Any]) -> list[ResilienceGap]:
        """Scans topology (nodes, edges, metrics, spofs, bottlenecks) and produces

        explicit ResilienceGap items for all 12 gap types.
        """
        gaps: list[ResilienceGap] = []
        nodes = topology.get("nodes", {})
        edges = topology.get("edges", [])
        spofs = set(topology.get("spofs", []))
        bottlenecks = set(topology.get("bottlenecks", []))

        # Compute incoming/outgoing degree
        in_degree: dict[str, int] = {k: 0 for k in nodes}
        out_degree: dict[str, int] = {k: 0 for k in nodes}
        for edge in edges:
            src = edge.get("source") or edge.get("from")
            dst = edge.get("target") or edge.get("to")
            if src in out_degree:
                out_degree[src] += 1
            if dst in in_degree:
                in_degree[dst] += 1

        for entity_id, meta in nodes.items():
            criticality = meta.get("criticality", 0.5)
            is_critical = criticality >= 0.7

            # 1. NO_REDUNDANCY & SINGLE_POINT_OF_FAILURE
            red_status, modes = self.evaluate_redundancy(entity_id, topology)
            if red_status == RedundancyType.NO_REDUNDANCY and is_critical:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_red"),
                        gap_type=ResilienceGapType.NO_REDUNDANCY,
                        affected_scope=meta.get("scope", "SERVICE"),
                        target_entity=entity_id,
                        severity="HIGH",
                        confidence=0.95,
                        evidence=[f"Criticality {criticality} with no configured backup nodes or failover"],
                        remediation_candidate=f"Deploy active or passive backup replica for {entity_id}",
                    )
                )

            if entity_id in spofs or (out_degree.get(entity_id, 0) >= 3 and in_degree.get(entity_id, 0) == 0 and red_status != RedundancyType.KNOWN_REDUNDANCY):
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_spof"),
                        gap_type=ResilienceGapType.SINGLE_POINT_OF_FAILURE,
                        affected_scope=meta.get("scope", "INFRASTRUCTURE"),
                        target_entity=entity_id,
                        severity="CRITICAL" if is_critical else "HIGH",
                        confidence=0.9,
                        evidence=[f"Component has high fan-out ({out_degree.get(entity_id, 0)}) and zero redundancy"],
                        remediation_candidate=f"Introduce redundant path or decoupled queue buffer for {entity_id}",
                    )
                )

            # 2. WEAK_CONTAINMENT
            has_circuit_breaker = meta.get("has_circuit_breaker", False)
            isolation_supported = meta.get("isolation_supported", False)
            if out_degree.get(entity_id, 0) >= 2 and not has_circuit_breaker and not isolation_supported:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_cnt"),
                        gap_type=ResilienceGapType.WEAK_CONTAINMENT,
                        affected_scope="PROPAGATION",
                        target_entity=entity_id,
                        severity="MEDIUM" if not is_critical else "HIGH",
                        confidence=0.85,
                        evidence=[f"Lacks circuit breaker or process isolation despite fan-out {out_degree.get(entity_id, 0)}"],
                        remediation_candidate=f"Wrap {entity_id} client calls in dynamic CircuitBreaker with bulkhead isolation",
                    )
                )

            # 3. SLOW_RECOVERY
            est_recovery_seconds = meta.get("recovery_time_seconds", 60.0)
            target_rto_seconds = meta.get("rto_seconds", 120.0)
            if est_recovery_seconds > target_rto_seconds:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_rto"),
                        gap_type=ResilienceGapType.SLOW_RECOVERY,
                        affected_scope="RTO",
                        target_entity=entity_id,
                        severity="MEDIUM",
                        confidence=0.8,
                        evidence=[f"Estimated recovery time {est_recovery_seconds}s exceeds target RTO {target_rto_seconds}s"],
                        remediation_candidate=f"Automate pre-warmed failover to reduce recovery time below {target_rto_seconds}s",
                    )
                )

            # 4. MISSING_ROLLBACK
            has_rollback = meta.get("has_rollback", True)
            if not has_rollback and is_critical:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_rol"),
                        gap_type=ResilienceGapType.MISSING_ROLLBACK,
                        affected_scope="REVERSIBILITY",
                        target_entity=entity_id,
                        severity="HIGH",
                        confidence=0.9,
                        evidence=["Critical mutation pathway has no automated rollback procedure"],
                        remediation_candidate=f"Implement compensating transactional rollback hook for {entity_id}",
                    )
                )

            # 5. INSUFFICIENT_OBSERVABILITY
            has_health_check = meta.get("has_health_check", True)
            metrics_reported = meta.get("metrics_reported", True)
            if not has_health_check or not metrics_reported:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_obs"),
                        gap_type=ResilienceGapType.INSUFFICIENT_OBSERVABILITY,
                        affected_scope="MONITORING",
                        target_entity=entity_id,
                        severity="MEDIUM",
                        confidence=0.88,
                        evidence=["Missing synthetic health probe or real-time metric telemetry"],
                        remediation_candidate=f"Register deterministic health check probe in Observability Registry for {entity_id}",
                    )
                )

            # 6. UNKNOWN_DEPENDENCY
            if meta.get("has_unknown_deps", False):
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_ukd"),
                        gap_type=ResilienceGapType.UNKNOWN_DEPENDENCY,
                        affected_scope="TOPOLOGY",
                        target_entity=entity_id,
                        severity="LOW",
                        confidence=0.75,
                        evidence=["Downstream call patterns include unmapped remote endpoints"],
                        remediation_candidate=f"Run dynamic tracing to map transitive dependencies for {entity_id}",
                    )
                )

            # 7. EXCESSIVE_COUPLING
            total_coupling = in_degree.get(entity_id, 0) + out_degree.get(entity_id, 0)
            if total_coupling >= 6:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_cpl"),
                        gap_type=ResilienceGapType.EXCESSIVE_COUPLING,
                        affected_scope="COUPLING",
                        target_entity=entity_id,
                        severity="HIGH",
                        confidence=0.9,
                        evidence=[f"High node degree ({total_coupling} edges) creates tight structural coupling"],
                        remediation_candidate=f"Decouple {entity_id} via event bus pub/sub or intermediary buffer",
                    )
                )

            # 8. SCARCE_RESOURCE
            resource_headroom = meta.get("resource_headroom", 1.0)
            if resource_headroom < 0.15 or entity_id in bottlenecks:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_res"),
                        gap_type=ResilienceGapType.SCARCE_RESOURCE,
                        affected_scope="CAPACITY",
                        target_entity=entity_id,
                        severity="HIGH",
                        confidence=0.85,
                        evidence=[f"Resource headroom is constrained at {round(resource_headroom * 100, 1)}%"],
                        remediation_candidate=f"Allocate additional resource pool or enable dynamic rate limiting for {entity_id}",
                    )
                )

            # 9. UNTESTED_RECOVERY_PATH
            if meta.get("recovery_tested", True) is False:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_unt"),
                        gap_type=ResilienceGapType.UNTESTED_RECOVERY_PATH,
                        affected_scope="TESTING",
                        target_entity=entity_id,
                        severity="MEDIUM",
                        confidence=0.8,
                        evidence=["Recovery routine has not been verified in sandbox or simulation"],
                        remediation_candidate=f"Schedule non-destructive simulation drill for {entity_id} failover",
                    )
                )

            # 10. UNVERIFIED_FALLBACK
            if meta.get("fallback_verified", True) is False:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_unv"),
                        gap_type=ResilienceGapType.UNVERIFIED_FALLBACK,
                        affected_scope="FALLBACK",
                        target_entity=entity_id,
                        severity="MEDIUM",
                        confidence=0.82,
                        evidence=["Fallback degraded mode contract has not been tested against real payloads"],
                        remediation_candidate=f"Run deterministic contract test on fallback handler for {entity_id}",
                    )
                )

            # 11. STALE_RECOVERY_PROCEDURE
            last_drill_days = meta.get("days_since_last_drill", 0)
            if last_drill_days > 90:
                gaps.append(
                    ResilienceGap(
                        gap_id=generate_defense_id("gap_stl"),
                        gap_type=ResilienceGapType.STALE_RECOVERY_PROCEDURE,
                        affected_scope="DRILL",
                        target_entity=entity_id,
                        severity="LOW",
                        confidence=0.78,
                        evidence=[f"Recovery procedure last verified {last_drill_days} days ago (>90d threshold)"],
                        remediation_candidate=f"Trigger automated dry-run validation drill for {entity_id}",
                    )
                )

        return gaps

    def build_scorecard(self, topology: dict[str, Any], gaps: list[ResilienceGap]) -> ResilienceScorecard:
        """Evaluates all 12 dimensions of resilience and synthesizes an interpretable scorecard."""
        nodes = topology.get("nodes", {})
        edges = topology.get("edges", [])
        spofs = set(topology.get("spofs", []))
        total_nodes = max(len(nodes), 1)

        # 1. Redundancy Dimension
        nodes_with_redundancy = sum(1 for n in nodes if self.evaluate_redundancy(n, topology)[0] == RedundancyType.KNOWN_REDUNDANCY)
        red_score = max(0.0, min(1.0, nodes_with_redundancy / total_nodes))
        dim_redundancy = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.REDUNDANCY,
            score=round(red_score, 2),
            evidence=[f"{nodes_with_redundancy}/{total_nodes} components have active/passive redundancy"],
            confidence=0.9,
        )

        # 2. Isolation Dimension
        isolated_nodes = sum(1 for n, m in nodes.items() if m.get("isolation_supported") or m.get("has_circuit_breaker"))
        iso_score = max(0.0, min(1.0, isolated_nodes / total_nodes))
        dim_isolation = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.ISOLATION,
            score=round(iso_score, 2),
            evidence=[f"{isolated_nodes}/{total_nodes} nodes support circuit-breaker or bulkhead isolation"],
            confidence=0.85,
        )

        # 3. Recoverability Dimension
        recoverable_nodes = sum(1 for n, m in nodes.items() if m.get("recoverable", True))
        rec_score = max(0.0, min(1.0, recoverable_nodes / total_nodes))
        dim_recoverability = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.RECOVERABILITY,
            score=round(rec_score, 2),
            evidence=[f"{recoverable_nodes}/{total_nodes} nodes have automated or guided recovery routines"],
            confidence=0.88,
        )

        # 4. Adaptability Dimension
        degradable_nodes = sum(1 for n, m in nodes.items() if m.get("supports_degraded_mode", True))
        adapt_score = max(0.0, min(1.0, degradable_nodes / total_nodes))
        dim_adaptability = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.ADAPTABILITY,
            score=round(adapt_score, 2),
            evidence=[f"{degradable_nodes}/{total_nodes} services can operate in controlled degraded mode"],
            confidence=0.8,
        )

        # 5. Observability Dimension
        observed_nodes = sum(1 for n, m in nodes.items() if m.get("has_health_check", True) and m.get("metrics_reported", True))
        obs_score = max(0.0, min(1.0, observed_nodes / total_nodes))
        dim_observability = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.OBSERVABILITY,
            score=round(obs_score, 2),
            evidence=[f"{observed_nodes}/{total_nodes} nodes have continuous health checks and telemetry"],
            confidence=0.92,
        )

        # 6. Fault Tolerance Dimension
        spof_penalty = len(spofs) * 0.15
        ft_score = max(0.0, min(1.0, 1.0 - spof_penalty))
        dim_fault_tolerance = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.FAULT_TOLERANCE,
            score=round(ft_score, 2),
            evidence=[f"{len(spofs)} single points of failure detected impacting systemic tolerance"],
            confidence=0.9,
        )

        # 7. Resource Slack Dimension
        headrooms = [m.get("resource_headroom", 0.5) for m in nodes.values()]
        avg_headroom = sum(headrooms) / len(headrooms) if headrooms else 0.5
        dim_resource_slack = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.RESOURCE_SLACK,
            score=round(max(0.0, min(1.0, avg_headroom)), 2),
            evidence=[f"Average resource headroom across cluster is {round(avg_headroom * 100, 1)}%"],
            confidence=0.85,
        )

        # 8. Dependency Diversity Dimension
        external_providers = {m.get("provider", "local") for m in nodes.values()}
        div_score = min(1.0, len(external_providers) * 0.3 + 0.4)
        dim_dependency_diversity = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.DEPENDENCY_DIVERSITY,
            score=round(div_score, 2),
            evidence=[f"{len(external_providers)} distinct infrastructure/service providers utilized"],
            confidence=0.8,
        )

        # 9. Recovery Speed Dimension
        speeds = [min(1.0, 60.0 / max(m.get("recovery_time_seconds", 60.0), 1.0)) for m in nodes.values()]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.7
        dim_recovery_speed = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.RECOVERY_SPEED,
            score=round(avg_speed, 2),
            evidence=[f"Estimated cluster MTTR efficiency score: {round(avg_speed, 2)}"],
            confidence=0.82,
        )

        # 10. Rollback Capability Dimension
        rollback_supported = sum(1 for n, m in nodes.items() if m.get("has_rollback", True))
        rol_score = max(0.0, min(1.0, rollback_supported / total_nodes))
        dim_rollback_capability = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.ROLLBACK_CAPABILITY,
            score=round(rol_score, 2),
            evidence=[f"{rollback_supported}/{total_nodes} components support automated transactional rollback"],
            confidence=0.89,
        )

        # 11. Human Fallback Dimension
        handoff_ready = sum(1 for n, m in nodes.items() if m.get("human_fallback_available", True))
        hf_score = max(0.0, min(1.0, handoff_ready / total_nodes))
        dim_human_fallback = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.HUMAN_FALLBACK,
            score=round(hf_score, 2),
            evidence=[f"{handoff_ready}/{total_nodes} operations have structured human escalation procedures"],
            confidence=0.85,
        )

        # 12. Containment Strength Dimension
        weak_cpts = sum(1 for g in gaps if g.gap_type == ResilienceGapType.WEAK_CONTAINMENT)
        cnt_score = max(0.0, min(1.0, 1.0 - (weak_cpts * 0.2)))
        dim_containment_strength = ResilienceDimensionScore(
            dimension=ResilienceDimensionType.CONTAINMENT_STRENGTH,
            score=round(cnt_score, 2),
            evidence=[f"{weak_cpts} weak containment points detected along cascade routes"],
            confidence=0.88,
        )

        dims: dict[str, ResilienceDimensionScore] = {
            ResilienceDimensionType.REDUNDANCY.value: dim_redundancy,
            ResilienceDimensionType.ISOLATION.value: dim_isolation,
            ResilienceDimensionType.RECOVERABILITY.value: dim_recoverability,
            ResilienceDimensionType.ADAPTABILITY.value: dim_adaptability,
            ResilienceDimensionType.OBSERVABILITY.value: dim_observability,
            ResilienceDimensionType.FAULT_TOLERANCE.value: dim_fault_tolerance,
            ResilienceDimensionType.RESOURCE_SLACK.value: dim_resource_slack,
            ResilienceDimensionType.DEPENDENCY_DIVERSITY.value: dim_dependency_diversity,
            ResilienceDimensionType.RECOVERY_SPEED.value: dim_recovery_speed,
            ResilienceDimensionType.ROLLBACK_CAPABILITY.value: dim_rollback_capability,
            ResilienceDimensionType.HUMAN_FALLBACK.value: dim_human_fallback,
            ResilienceDimensionType.CONTAINMENT_STRENGTH.value: dim_containment_strength,
        }

        # Weighted composite score
        overall_index = sum(d.score for d in dims.values()) / len(dims)
        bottleneck_dims = [
            ResilienceDimensionType(d.dimension) for d in dims.values() if d.score < 0.6
        ]

        critical_gaps_count = sum(1 for g in gaps if g.severity in ("HIGH", "CRITICAL"))
        rationale = (
            f"Evaluated 12 dimensions across {total_nodes} nodes. Overall resilience index is {round(overall_index, 2)}. "
            f"Detected {len(gaps)} gaps ({critical_gaps_count} high/critical). "
            f"Key bottlenecks: {[b.value for b in bottleneck_dims] or 'None'}."
        )

        return ResilienceScorecard(
            dimensions=dims,
            overall_resilience_index=round(overall_index, 2),
            rationale=rationale,
            bottleneck_dimensions=bottleneck_dims,
        )
