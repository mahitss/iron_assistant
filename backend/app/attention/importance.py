"""Independent Importance Evaluation Engine for Kairo Attention (Task 70).

Importance represents long-term consequence and strategic value:
- mission & goal impact
- business and operational stability
- user consequence
- security integrity
- financial/resource blast radius
- dependency depth (how many downstream items depend on this)

Importance is strictly decoupled from recency, novelty, and urgency:
- A new event is not automatically important.
- An urgent event is not automatically important.
"""


class ImportanceEvaluator:
    """Computes explainable importance scores independently from urgency."""

    WEIGHT_MISSION_GOAL = 0.30
    WEIGHT_SECURITY_SYSTEM = 0.30
    WEIGHT_DEPENDENCY_DEPTH = 0.20
    WEIGHT_USER_STRATEGIC = 0.20

    @classmethod
    def evaluate(
        cls,
        *,
        mission_refs: list[str] | None = None,
        goal_refs: list[str] | None = None,
        incident_refs: list[str] | None = None,
        downstream_dependency_count: int = 0,
        security_criticality: float = 0.0,
        system_blast_radius: float = 0.0,
        user_impact_level: float = 0.0,
        strategic_value: float = 0.0,
        explicit_importance: float | None = None,
    ) -> tuple[float, str, dict[str, float]]:
        """Evaluate importance.

        Returns:
            (importance_score [0.0 - 1.0], importance_tier, component_breakdown)
        """
        # 1. Mission & Goal alignment impact
        num_goals = len(goal_refs or [])
        num_missions = len(mission_refs or [])
        goal_mission_factor = min(1.0, (num_goals * 0.3) + (num_missions * 0.4))

        # 2. Security and system stability impact
        num_incidents = len(incident_refs or [])
        incident_factor = min(1.0, num_incidents * 0.5)
        sec_sys_factor = min(
            1.0,
            max(
                security_criticality,
                system_blast_radius,
                incident_factor,
            ),
        )

        # 3. Dependency depth impact (unblocking downstream work)
        dep_factor = min(1.0, downstream_dependency_count * 0.15)

        # 4. User impact and strategic value
        user_strat_factor = min(1.0, max(user_impact_level, strategic_value))

        # Multi-domain composite with dominant factor protection
        # A critically strategic or mission-critical item should not be diluted to low importance
        # merely because there is no simultaneous active security incident.
        active_factors = [goal_mission_factor, sec_sys_factor, dep_factor, user_strat_factor]
        max_factor = max(active_factors) if active_factors else 0.0
        weighted_avg = (
            cls.WEIGHT_MISSION_GOAL * goal_mission_factor
            + cls.WEIGHT_SECURITY_SYSTEM * sec_sys_factor
            + cls.WEIGHT_DEPENDENCY_DEPTH * dep_factor
            + cls.WEIGHT_USER_STRATEGIC * user_strat_factor
        )
        computed_importance = (max_factor * 0.65) + (weighted_avg * 0.35)

        if explicit_importance is not None:
            clamped_explicit = max(0.0, min(1.0, explicit_importance))
            final_importance = max(computed_importance, clamped_explicit)
        else:
            final_importance = computed_importance

        final_importance = round(max(0.0, min(1.0, final_importance)), 3)

        if final_importance >= 0.85:
            tier = "CRITICAL"
        elif final_importance >= 0.70:
            tier = "HIGH"
        elif final_importance >= 0.40:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        breakdown = {
            "mission_goal_alignment": round(goal_mission_factor, 3),
            "security_system_impact": round(sec_sys_factor, 3),
            "dependency_impact": round(dep_factor, 3),
            "user_strategic_value": round(user_strat_factor, 3),
            "computed_importance": final_importance,
        }

        return final_importance, tier, breakdown
