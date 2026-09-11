"""Adaptive Defense & Post-Incident Learning Engine (Task 76).

Coordinates:
1. Post-Incident Learning (What was expected, What happened, Why it mattered, What should change)
2. Epistemic Knowledge Lifecycle: OBSERVED -> HYPOTHESIZED -> VALIDATED -> TRUSTED
3. Operational Metrics: MTTD, MTTC, MTTR calculations (refusing to claim 'mean' when samples < 3)
4. Bounded Adaptive Defense Recommendations:
   NEVER autonomously weakens security policies or bypasses controls.
   Can recommend tightening monitoring, adding redundancy, or requiring additional approvals.
"""

from datetime import UTC, datetime
from typing import Any

from app.resilience.defense_schemas import (
    AdaptiveDefenseRecommendation,
    KnowledgeLifecycleState,
    PostIncidentLesson,
    RecoveryPlan,
    ResilienceTrendMetrics,
    generate_defense_id,
    utc_now,
)


class AdaptiveDefenseEngine:
    """Extracts lessons from incident resolutions and proposes bounded structural adaptations."""

    def __init__(self) -> None:
        self.lessons_store: list[PostIncidentLesson] = []
        self.recommendations_store: list[AdaptiveDefenseRecommendation] = []
        self.incident_history: list[dict[str, Any]] = []

    def record_incident_timing(
        self,
        incident_id: str,
        detection_duration_s: float,
        containment_duration_s: float,
        recovery_duration_s: float,
        success: bool,
    ) -> None:
        """Stores timing record for historical MTTD / MTTC / MTTR analytics."""
        self.incident_history.append({
            "incident_id": incident_id,
            "detection_duration_s": detection_duration_s,
            "containment_duration_s": containment_duration_s,
            "recovery_duration_s": recovery_duration_s,
            "success": success,
            "timestamp": utc_now(),
        })

    def calculate_resilience_trends(self) -> ResilienceTrendMetrics:
        """Computes MTTD, MTTC, MTTR metrics.

        Explicit requirement: Do not claim 'mean' if insufficient observations exist (< 3 samples).
        """
        successful_incidents = [i for i in self.incident_history if i.get("success")]
        sample_size = len(successful_incidents)

        if sample_size < 3:
            return ResilienceTrendMetrics(
                mttd_seconds=None,
                mttc_seconds=None,
                mttr_seconds=None,
                sample_size=sample_size,
                trend_direction="INSUFFICIENT_DATA",
                recurring_weaknesses=[],
            )

        mttd = sum(i["detection_duration_s"] for i in successful_incidents) / sample_size
        mttc = sum(i["containment_duration_s"] for i in successful_incidents) / sample_size
        mttr = sum(i["recovery_duration_s"] for i in successful_incidents) / sample_size

        # Determine trend direction from first half vs second half if sample_size >= 4
        trend = "STABLE"
        if sample_size >= 4:
            mid = sample_size // 2
            first_half_mttr = sum(i["recovery_duration_s"] for i in successful_incidents[:mid]) / mid
            second_half_mttr = sum(i["recovery_duration_s"] for i in successful_incidents[mid:]) / (sample_size - mid)
            if second_half_mttr < first_half_mttr * 0.85:
                trend = "IMPROVING"
            elif second_half_mttr > first_half_mttr * 1.15:
                trend = "DEGRADING"

        return ResilienceTrendMetrics(
            mttd_seconds=round(mttd, 2),
            mttc_seconds=round(mttc, 2),
            mttr_seconds=round(mttr, 2),
            sample_size=sample_size,
            trend_direction=trend,
            recurring_weaknesses=[],
        )

    def extract_post_incident_lesson(
        self,
        incident_id: str,
        plan: RecoveryPlan,
        what_happened: str,
        why_it_mattered: str,
        what_should_change: str,
    ) -> PostIncidentLesson:
        """Distills a post-incident outcome into structured knowledge with OBSERVED lifecycle state."""
        lesson = PostIncidentLesson(
            lesson_id=generate_defense_id("les"),
            incident_id=incident_id,
            recovery_plan_id=plan.plan_id,
            what_was_expected=f"Recovery strategy {plan.selected_strategy.value} was expected to restore service within {plan.recovery_paths[0].expected_duration_seconds if plan.recovery_paths else 60}s.",
            what_happened=what_happened,
            why_it_mattered=why_it_mattered,
            what_should_change=what_should_change,
            status=KnowledgeLifecycleState.OBSERVED,
            learned_at=utc_now(),
        )
        self.lessons_store.append(lesson)
        return lesson

    def promote_lesson_lifecycle(
        self,
        lesson_id: str,
        target_state: KnowledgeLifecycleState,
    ) -> PostIncidentLesson:
        """Promotes learned knowledge across OBSERVED -> HYPOTHESIZED -> VALIDATED -> TRUSTED."""
        for les in self.lessons_store:
            if les.lesson_id == lesson_id:
                les.status = target_state
                return les
        raise ValueError(f"Lesson {lesson_id} not found")

    def generate_adaptive_recommendations(
        self,
        lessons: list[PostIncidentLesson],
        failed_entity: str,
    ) -> list[AdaptiveDefenseRecommendation]:
        """Generates bounded, reversible resilience recommendations.

        Invariant: Never weakens security policies or approval gates.
        """
        recs: list[AdaptiveDefenseRecommendation] = []

        # Propose adding redundancy
        recs.append(
            AdaptiveDefenseRecommendation(
                recommendation_id=generate_defense_id("rec_red"),
                recommendation_type="ADD_REDUNDANCY",
                target_entity=failed_entity,
                justification=f"Post-incident analysis for {failed_entity} revealed single-point fragility during outage.",
                confidence=0.88,
                cost="MEDIUM",
                reversibility=True,
                risk_reduction=0.45,
                requires_approval=True,
            )
        )

        # Propose tightening circuit breaker
        recs.append(
            AdaptiveDefenseRecommendation(
                recommendation_id=generate_defense_id("rec_cb"),
                recommendation_type="TIGHTEN_CIRCUIT_BREAKER",
                target_entity=failed_entity,
                justification="Lower error threshold to 3 consecutive failures to contain cascading propagation faster.",
                confidence=0.92,
                cost="LOW",
                reversibility=True,
                risk_reduction=0.3,
                requires_approval=True,
            )
        )

        self.recommendations_store.extend(recs)
        return recs
