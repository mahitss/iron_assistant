"""Counterexample Engine for Kairo Strategy Engine (Task 106).

Maintains, indexes, and queries boundary exceptions, failure cases, adversarial conditions,
and environmental shifts so that tail risks are never masked by high average success rates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.strategy.domain import EvidenceSourceType, StrategyEvidence, utc_now

logger = logging.getLogger("kairo.strategy.counterexample_engine")


class CounterexampleMatch(BaseModel):
    """Result of checking a context against known counterexamples."""

    has_exact_match: bool = False
    has_partial_match: bool = False
    matching_counterexamples: List[StrategyEvidence] = Field(default_factory=list)
    risk_summary: str = ""
    penalty_recommended: float = 0.0


class CounterexampleEngine:
    """Manages counterexamples and exceptions for strategies."""

    def __init__(self) -> None:
        self._counterexamples: Dict[str, List[StrategyEvidence]] = {}

    def register_counterexample(
        self,
        strategy_id: str,
        claim: str,
        failure_context: Dict[str, Any],
        observed_metrics: Optional[Dict[str, Any]] = None,
        source_id: str = "runtime_failure",
        capability_version: str = "1.0.0",
    ) -> StrategyEvidence:
        """Register a new counterexample against a strategy."""
        evidence = StrategyEvidence(
            strategy_id=strategy_id,
            source_type=EvidenceSourceType.COUNTEREXAMPLE,
            source_id=source_id,
            is_counterexample=True,
            claim=claim,
            observed_metrics=observed_metrics or {},
            environmental_context=failure_context,
            capability_version=capability_version,
            confidence_weight=1.0,
            verified=True,
        )
        evidence.seal()

        if strategy_id not in self._counterexamples:
            self._counterexamples[strategy_id] = []
        self._counterexamples[strategy_id].append(evidence)

        logger.warning(
            f"Registered counterexample for strategy {strategy_id}: '{claim}' with context {failure_context}"
        )
        return evidence

    def get_counterexamples(self, strategy_id: str) -> List[StrategyEvidence]:
        """Retrieve all counterexamples for a given strategy."""
        return self._counterexamples.get(strategy_id, [])

    def check_context_against_counterexamples(
        self,
        strategy_id: str,
        context: Dict[str, Any],
    ) -> CounterexampleMatch:
        """Check if current operating context matches any known counterexample conditions."""
        counterexamples = self.get_counterexamples(strategy_id)
        if not counterexamples:
            return CounterexampleMatch(has_exact_match=False, has_partial_match=False)

        exact_matches: List[StrategyEvidence] = []
        partial_matches: List[StrategyEvidence] = []

        for ce in counterexamples:
            ce_ctx = ce.environmental_context
            matched_keys = 0
            total_keys = len(ce_ctx)

            if total_keys == 0:
                continue

            for k, v in ce_ctx.items():
                if k in context and context[k] == v:
                    matched_keys += 1

            if matched_keys == total_keys:
                exact_matches.append(ce)
            elif matched_keys > 0:
                partial_matches.append(ce)

        if exact_matches:
            return CounterexampleMatch(
                has_exact_match=True,
                has_partial_match=True,
                matching_counterexamples=exact_matches,
                risk_summary=f"Context EXACTLY matches {len(exact_matches)} historical counterexample(s) where strategy failed!",
                penalty_recommended=0.45,
            )
        elif partial_matches:
            return CounterexampleMatch(
                has_exact_match=False,
                has_partial_match=True,
                matching_counterexamples=partial_matches,
                risk_summary=f"Context partially overlaps with {len(partial_matches)} historical failure condition(s).",
                penalty_recommended=0.15,
            )

        return CounterexampleMatch(has_exact_match=False, has_partial_match=False)
