"""Structured Multi-Dimensional Mission Health Engine (Task 100)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    MilestoneStatus,
    Mission,
    MissionHealth,
    MissionHealthDimensions,
)

logger = logging.getLogger("kairo.missions.health")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionHealthEngine:
    """Evaluates raw operational health dimensions and derives transparent health classifications."""

    @classmethod
    def evaluate_health(
        cls,
        mission: Mission,
        resource_stats: dict[str, Any] | None = None,
        situation_stats: dict[str, Any] | None = None,
        capability_stats: dict[str, Any] | None = None,
    ) -> tuple[MissionHealth, MissionHealthDimensions]:
        """Compute raw dimensions and derive summary status with derivation rationale.

        Dimensions:
        - progress: Verified milestone completion ratio.
        - risk: Overall mission risk level.
        - blockers: Active blockers or blocked milestones.
        - uncertainty: Epistemic uncertainty based on unverified assumptions.
        - dependency_health: Ratio of available vs blocked/degraded dependencies.
        - resource_health: Budget utilization runway.
        - reliability: Reliability score based on failure counts.
        - deadline_pressure: Schedule compression relative to deadline.
        - situation_pressure: Severity of linked active situations.
        - capability_readiness: Status of required runtime capabilities.
        """
        now = _now_utc()

        # 1. Progress ratio
        total_m = len(mission.milestones)
        completed_m = sum(1 for m in mission.milestones if m.status == MilestoneStatus.COMPLETED)
        progress = (completed_m / total_m) if total_m > 0 else (mission.progress_pct / 100.0)

        # 2. Blockers
        active_blockers = len(mission.blockers) + sum(
            1 for m in mission.milestones if m.status == MilestoneStatus.BLOCKED
        )

        # 3. Uncertainty
        total_assumptions = len(mission.assumptions)
        unverified_count = sum(1 for a in mission.assumptions if a.status.value in ("UNVERIFIED", "UNKNOWN", "AT_RISK"))
        uncertainty = (unverified_count / total_assumptions) if total_assumptions > 0 else mission.uncertainty

        # 4. Dependency health
        total_deps = len(mission.dependencies)
        degraded_deps = sum(1 for d in mission.dependencies if d.status.value in ("BLOCKED", "DEGRADED", "FAILED"))
        dependency_health = 1.0 - (degraded_deps / total_deps) if total_deps > 0 else 1.0

        # 5. Resource health
        resource_health = 1.0
        if mission.budget_limits and mission.budget_consumed:
            max_cost = mission.budget_limits.get("max_cost_usd", 50.0)
            cost = mission.budget_consumed.get("cost_usd", 0.0)
            if max_cost > 0:
                resource_health = max(0.0, 1.0 - (cost / max_cost))

        # 6. Deadline pressure
        deadline_pressure = 0.0
        if mission.deadline:
            total_duration = (mission.deadline - mission.created_at).total_seconds()
            remaining = (mission.deadline - now).total_seconds()
            if total_duration > 0:
                if remaining <= 0:
                    deadline_pressure = 1.0
                else:
                    elapsed_ratio = 1.0 - (remaining / total_duration)
                    # If elapsed time significantly outpaces progress, high pressure
                    deadline_pressure = min(1.0, max(0.0, elapsed_ratio - progress + 0.2))

        # 7. Situation pressure
        situation_count = len(mission.active_situations)
        situation_pressure = min(1.0, situation_count * 0.25)
        if situation_stats:
            critical_count = situation_stats.get("critical_count", 0)
            if critical_count > 0:
                situation_pressure = 1.0

        # 8. Capability readiness
        capability_readiness = 1.0
        if capability_stats:
            capability_readiness = capability_stats.get("readiness_score", 1.0)

        # 9. Reliability
        failed_count = mission.failed_milestones + sum(1 for m in mission.milestones if m.status == MilestoneStatus.FAILED)
        reliability = max(0.0, 1.0 - (failed_count * 0.2))

        # 10. Risk
        risk = max(
            situation_pressure * 0.4 + deadline_pressure * 0.3 + (1.0 - dependency_health) * 0.3,
            0.1 if active_blockers == 0 else 0.5,
        )

        # Derive transparent health status
        reasons: list[str] = []
        if active_blockers > 0:
            derived_health = MissionHealth.BLOCKED
            reasons.append(f"{active_blockers} active blocker(s) halting progression")
        elif risk >= 0.7 or situation_pressure >= 0.7 or deadline_pressure >= 0.85:
            derived_health = MissionHealth.AT_RISK
            if situation_pressure >= 0.7:
                reasons.append("High situation pressure from active system alerts")
            if deadline_pressure >= 0.85:
                reasons.append("Severe deadline compression")
            if risk >= 0.7:
                reasons.append(f"Elevated composite risk score ({risk:.2f})")
        elif dependency_health < 0.6 or capability_readiness < 0.7:
            derived_health = MissionHealth.DEGRADED
            reasons.append(f"Subsystems degraded (dep_health={dependency_health:.2f}, cap_readiness={capability_readiness:.2f})")
        elif progress >= 1.0 and completed_m == total_m and total_m > 0:
            derived_health = MissionHealth.COMPLETED
            reasons.append("All milestones completed and verified")
        else:
            derived_health = MissionHealth.ON_TRACK
            reasons.append("Operations proceeding within nominal boundaries")

        summary_explanation = "; ".join(reasons)

        dimensions = MissionHealthDimensions(
            progress=round(progress, 3),
            risk=round(risk, 3),
            blockers=active_blockers,
            uncertainty=round(uncertainty, 3),
            dependency_health=round(dependency_health, 3),
            resource_health=round(resource_health, 3),
            reliability=round(reliability, 3),
            deadline_pressure=round(deadline_pressure, 3),
            situation_pressure=round(situation_pressure, 3),
            capability_readiness=round(capability_readiness, 3),
            summary_explanation=summary_explanation,
        )

        mission.health = derived_health
        mission.health_dimensions = dimensions
        mission.updated_at = now

        return derived_health, dimensions
