"""Independent Urgency Evaluation Engine for Kairo Attention (Task 70).

Urgency represents time-sensitivity:
- deadline proximity
- time-to-impact
- rate-of-change
- escalation probability
- irreversibility

Urgency is strictly independent of Importance:
- A task can be High Importance and Low Urgency (e.g., long-term architectural research).
- A task can be Low Importance and Critical Urgency (e.g., meeting starts in 2 minutes).
- Production database outage is Critical Importance AND Critical Urgency.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


class UrgencyEvaluator:
    """Computes explainable urgency scores independently from importance."""

    # Weights for urgency components
    WEIGHT_TIME_TO_IMPACT = 0.35
    WEIGHT_RATE_OF_CHANGE = 0.25
    WEIGHT_ESCALATION_PROBABILITY = 0.25
    WEIGHT_IRREVERSIBILITY = 0.15

    @classmethod
    def evaluate(
        cls,
        *,
        deadline: datetime | None = None,
        estimated_duration_sec: int = 300,
        rate_of_change: float = 0.0,
        escalation_probability: float = 0.0,
        is_irreversible: bool = False,
        source_is_trusted: bool = True,
        explicit_urgency: float | None = None,
    ) -> tuple[float, str, dict[str, float]]:
        """Evaluate urgency.

        Returns:
            (urgency_score [0.0 - 1.0], urgency_tier, component_breakdown)
        """
        # 1. Deadline pressure & time-to-impact calculation
        deadline_pressure = 0.0
        if deadline:
            now = utc_now()
            # Ensure timezone-aware comparison
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)

            seconds_remaining = (deadline - now).total_seconds()
            if seconds_remaining <= 0:
                # Overdue or immediate
                deadline_pressure = 1.0
            elif seconds_remaining < estimated_duration_sec:
                # Less time than required to complete
                deadline_pressure = 0.95
            elif seconds_remaining < estimated_duration_sec * 2:
                deadline_pressure = 0.80
            elif seconds_remaining < 3600:  # < 1 hour
                deadline_pressure = 0.60
            elif seconds_remaining < 86400:  # < 24 hours
                deadline_pressure = 0.35
            else:
                deadline_pressure = 0.10

            # Prevent deadline gaming: if source is untrusted, dampen deadline pressure
            if not source_is_trusted:
                deadline_pressure = min(deadline_pressure, 0.40)

        # 2. Rate of change (e.g., metric spikes, failure rate acceleration)
        clamped_rate = max(0.0, min(1.0, rate_of_change))

        # 3. Escalation probability (likelihood of cascading failure)
        clamped_escalation = max(0.0, min(1.0, escalation_probability))

        # 4. Irreversibility factor
        irreversibility_factor = 0.85 if is_irreversible else 0.10

        # Baseline composite calculation with dominant urgency factor protection
        active_urg_factors = [deadline_pressure, clamped_rate, clamped_escalation]
        max_factor = max(active_urg_factors) if active_urg_factors else 0.0
        weighted_avg = (
            cls.WEIGHT_TIME_TO_IMPACT * deadline_pressure
            + cls.WEIGHT_RATE_OF_CHANGE * clamped_rate
            + cls.WEIGHT_ESCALATION_PROBABILITY * clamped_escalation
            + cls.WEIGHT_IRREVERSIBILITY * irreversibility_factor
        )
        computed_urgency = (max_factor * 0.65) + (weighted_avg * 0.35)

        # If explicit urgency provided by validated domain entity (e.g. incident engine), blend safely
        if explicit_urgency is not None:
            clamped_explicit = max(0.0, min(1.0, explicit_urgency))
            if source_is_trusted:
                final_urgency = max(computed_urgency, clamped_explicit)
            else:
                # Untrusted claims of high urgency cannot bypass computed bounds
                final_urgency = min(clamped_explicit, computed_urgency + 0.2)
        else:
            final_urgency = computed_urgency

        final_urgency = round(max(0.0, min(1.0, final_urgency)), 3)

        if final_urgency >= 0.85:
            tier = "CRITICAL"
        elif final_urgency >= 0.70:
            tier = "HIGH"
        elif final_urgency >= 0.40:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        breakdown = {
            "deadline_pressure": round(deadline_pressure, 3),
            "rate_of_change": round(clamped_rate, 3),
            "escalation_probability": round(clamped_escalation, 3),
            "irreversibility": round(irreversibility_factor, 3),
            "computed_urgency": final_urgency,
        }

        return final_urgency, tier, breakdown
