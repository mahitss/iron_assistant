"""Deterministic, Explainable Attention Scoring Engine (Task 70).

Computes composite attention score:
  Factors:
    + importance (0.25)
    + urgency (0.25)
    + risk (0.20)
    + goal_alignment (0.10)
    + deadline_pressure (0.05)
    + dependency_impact (0.05)
    + novelty (0.05)
    + uncertainty (0.05)
  Penalties:
    - resource_cost
    - redundancy
    - staleness

Exposes full factor breakdown for complete explainability:
"Incident X received high attention because: severity=critical, risk=high, goal_alignment=high..."
"""

from app.attention.schemas import AttentionScoreBreakdown, AttentionThreshold


class AttentionScoringEngine:
    """Deterministic, explainable scoring engine for cognitive attention."""

    WEIGHT_IMPORTANCE = 0.30
    WEIGHT_URGENCY = 0.30
    WEIGHT_RISK = 0.20
    WEIGHT_GOAL_ALIGNMENT = 0.10
    WEIGHT_DEADLINE_PRESSURE = 0.04
    WEIGHT_DEPENDENCY_IMPACT = 0.03
    WEIGHT_NOVELTY = 0.02
    WEIGHT_UNCERTAINTY = 0.01

    # Threshold boundaries
    THRESHOLD_IGNORE = 0.20
    THRESHOLD_LOW = 0.40
    THRESHOLD_NORMAL = 0.70
    THRESHOLD_HIGH = 0.85

    @classmethod
    def score(
        cls,
        *,
        importance: float,
        urgency: float,
        risk: float,
        severity: str = "MEDIUM",
        goal_alignment: float = 0.5,
        deadline_pressure: float = 0.0,
        dependency_impact: float = 0.0,
        novelty: float = 0.0,
        uncertainty: float = 0.2,
        change_magnitude: float = 0.0,
        resource_cost: float = 0.1,
        redundancy: float = 0.0,
        staleness: float = 0.0,
        aging_boost: float = 0.0,
        is_adversarial_suppressed: bool = False,
    ) -> tuple[float, AttentionThreshold, AttentionScoreBreakdown]:
        """Compute transparent, deterministic attention score and explanation."""
        # 1. Clamping inputs
        imp = max(0.0, min(1.0, importance))
        urg = max(0.0, min(1.0, urgency))
        rsk = max(0.0, min(1.0, risk))
        goal = max(0.0, min(1.0, goal_alignment))
        dl = max(0.0, min(1.0, deadline_pressure))
        dep = max(0.0, min(1.0, dependency_impact))
        nov = max(0.0, min(1.0, novelty))
        unc = max(0.0, min(1.0, uncertainty))
        chg = max(0.0, min(1.0, change_magnitude))

        # 2. Penalties
        cost_pen = max(0.0, min(0.15, resource_cost * 0.15))
        red_pen = max(0.0, min(0.20, redundancy * 0.20))
        stale_pen = max(0.0, min(0.20, staleness * 0.20))

        # 3. Additive composite factors
        raw_score = (
            cls.WEIGHT_IMPORTANCE * imp
            + cls.WEIGHT_URGENCY * urg
            + cls.WEIGHT_RISK * rsk
            + cls.WEIGHT_GOAL_ALIGNMENT * goal
            + cls.WEIGHT_DEADLINE_PRESSURE * dl
            + cls.WEIGHT_DEPENDENCY_IMPACT * dep
            + cls.WEIGHT_NOVELTY * nov
            + cls.WEIGHT_UNCERTAINTY * unc
        )

        # Severity boost
        severity_boost = 0.0
        if severity == "CRITICAL":
            severity_boost = 0.10
        elif severity == "HIGH":
            severity_boost = 0.05
        raw_score += severity_boost

        # Modulate by change magnitude if present
        if chg > 0.5:
            raw_score += (chg - 0.5) * 0.1

        # Fairness aging boost (prevents starvation of deferred items)
        raw_score += max(0.0, min(0.25, aging_boost))

        # Deduct penalties
        net_score = raw_score - (cost_pen + red_pen + stale_pen)

        # Adversarial suppression penalty if detected
        if is_adversarial_suppressed:
            net_score = min(0.35, net_score * 0.4)

        final_score = round(max(0.0, min(1.0, net_score)), 3)

        # 4. Map threshold
        if final_score < cls.THRESHOLD_IGNORE:
            threshold = AttentionThreshold.IGNORE
        elif final_score < cls.THRESHOLD_LOW:
            threshold = AttentionThreshold.LOW
        elif final_score < cls.THRESHOLD_NORMAL:
            threshold = AttentionThreshold.NORMAL
        elif final_score < cls.THRESHOLD_HIGH:
            threshold = AttentionThreshold.HIGH
        else:
            threshold = AttentionThreshold.CRITICAL

        # 5. Build contributing factors and explanation
        factors: list[str] = []
        if imp >= 0.70:
            factors.append(f"high importance ({imp:.2f})")
        if urg >= 0.70:
            factors.append(f"critical urgency ({urg:.2f})")
        if rsk >= 0.70:
            factors.append(f"elevated risk ({rsk:.2f})")
        if goal >= 0.70:
            factors.append(f"strong goal alignment ({goal:.2f})")
        if dl >= 0.70:
            factors.append(f"urgent deadline pressure ({dl:.2f})")
        if dep >= 0.50:
            factors.append(f"high dependency impact ({dep:.2f})")
        if nov >= 0.70:
            factors.append(f"high novelty ({nov:.2f})")
        if aging_boost > 0.05:
            factors.append(f"fairness aging boost (+{aging_boost:.2f})")
        if cost_pen > 0.05:
            factors.append(f"high resource cost penalty (-{cost_pen:.2f})")
        if red_pen > 0.05:
            factors.append(f"redundancy penalty (-{red_pen:.2f})")
        if stale_pen > 0.05:
            factors.append(f"staleness penalty (-{stale_pen:.2f})")
        if is_adversarial_suppressed:
            factors.append("adversarial suppression penalty applied")

        if not factors:
            factors.append("baseline standard priority")

        explanation = (
            f"Attention score {final_score:.3f} ({threshold.value}) driven by: {', '.join(factors)}."
        )

        breakdown = AttentionScoreBreakdown(
            importance=imp,
            urgency=urg,
            risk=rsk,
            goal_alignment=goal,
            deadline_pressure=dl,
            dependency_impact=dep,
            novelty=nov,
            uncertainty=unc,
            change_magnitude=chg,
            resource_cost_penalty=cost_pen,
            redundancy_penalty=red_pen,
            staleness_penalty=stale_pen,
            composite_score=final_score,
            contributing_factors=factors,
            explanation=explanation,
        )

        return final_score, threshold, breakdown
