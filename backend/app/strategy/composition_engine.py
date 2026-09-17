"""Strategy Composition Engine for Kairo Strategy Engine (Task 106).

Supports composing complementary strategies into bounded execution chains while strictly
preventing recursive loops, infinite expansion, and circular dependencies (max depth 3).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.strategy.domain import Strategy, generate_id, utc_now

logger = logging.getLogger("kairo.strategy.composition_engine")


class StrategyChainStep(BaseModel):
    step_number: int
    strategy_id: str
    strategy_name: str
    category: str
    expected_output: str


class StrategyChain(BaseModel):
    chain_id: str
    name: str
    steps: List[StrategyChainStep]
    overall_confidence: float
    max_depth_exceeded: bool = False
    cycle_detected: bool = False
    validation_notes: List[str] = Field(default_factory=list)


class CompositionEngine:
    """Safely composes strategies into validated chains."""

    def __init__(self, max_depth: int = 3) -> None:
        self.max_depth = max_depth

    def compose_chain(
        self,
        name: str,
        strategies: List[Strategy],
    ) -> StrategyChain:
        """Compose a list of strategies into a bounded execution sequence."""
        chain_id = generate_id("schain")
        notes: List[str] = []
        steps: List[StrategyChainStep] = []

        # 1. Depth Limit Check
        if len(strategies) > self.max_depth:
            notes.append(
                f"Bounded composition violation: Chain length ({len(strategies)}) exceeds maximum allowed depth ({self.max_depth})."
            )
            return StrategyChain(
                chain_id=chain_id,
                name=name,
                steps=[],
                overall_confidence=0.0,
                max_depth_exceeded=True,
                cycle_detected=False,
                validation_notes=notes,
            )

        # 2. Cycle Detection
        seen_ids = set()
        for idx, strat in enumerate(strategies):
            if strat.id in seen_ids:
                notes.append(f"Cycle detected: Strategy '{strat.id}' repeated in chain step {idx + 1}.")
                return StrategyChain(
                    chain_id=chain_id,
                    name=name,
                    steps=[],
                    overall_confidence=0.0,
                    max_depth_exceeded=False,
                    cycle_detected=True,
                    validation_notes=notes,
                )
            seen_ids.add(strat.id)

            steps.append(
                StrategyChainStep(
                    step_number=idx + 1,
                    strategy_id=strat.id,
                    strategy_name=strat.name,
                    category=strat.category.value,
                    expected_output=strat.recommended_approach[:80],
                )
            )

        # 3. Aggregate Confidence (Weakest link principle)
        confidences = [s.confidence for s in strategies]
        chain_conf = min(confidences) if confidences else 0.5
        notes.append(f"Chain composed cleanly of {len(steps)} bounded steps.")

        logger.info(f"Composed strategy chain '{name}' ({chain_id}) with {len(steps)} steps (conf={chain_conf:.2f}).")
        return StrategyChain(
            chain_id=chain_id,
            name=name,
            steps=steps,
            overall_confidence=round(chain_conf, 3),
            max_depth_exceeded=False,
            cycle_detected=False,
            validation_notes=notes,
        )
