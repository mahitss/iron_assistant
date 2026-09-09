"""Confidence estimation scoring for structured intent resolution (Spec 37, 73)."""

from app.intent.schemas import ResolutionMethod


class ConfidenceEstimator:
    """Estimates interpretation and resolution confidence score (0.0 to 1.0)."""

    BASE_SCORES = {
        ResolutionMethod.EXPLICIT: 1.0,
        ResolutionMethod.EXACT_MATCH: 0.98,
        ResolutionMethod.ALIAS: 0.88,
        ResolutionMethod.CONTEXT: 0.82,
        ResolutionMethod.FUZZY_MATCH: 0.60,
        ResolutionMethod.MODEL_INFERENCE: 0.65,
    }

    @classmethod
    def estimate(
        cls,
        resolution_methods: list[ResolutionMethod] | None = None,
        has_ambiguity: bool = False,
        missing_params_count: int = 0,
    ) -> float:
        """
        Calculates confidence strictly as an interpretation metric.
        INVARIANT (Spec 37): High confidence NEVER authorizes privileged actions or bypasses security checks.
        """
        if not resolution_methods:
            base = 0.85
        else:
            scores = [cls.BASE_SCORES.get(m, 0.70) for m in resolution_methods]
            base = min(scores)

        # Penalize for ambiguity or missing required parameters
        if has_ambiguity:
            base *= 0.60

        if missing_params_count > 0:
            penalty = min(0.40, missing_params_count * 0.15)
            base -= penalty

        return round(max(0.10, min(1.0, base)), 2)
