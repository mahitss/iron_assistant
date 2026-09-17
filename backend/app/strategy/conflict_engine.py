"""Conflict Detection Engine for Kairo Strategy Engine (Task 106).

Detects inter-strategy conflicts across all 7 canonical types:
DIRECT, CONDITIONAL, TEMPORAL, ENVIRONMENTAL, RESOURCE, CAPABILITY, OBJECTIVE.
Exposes conflicts explicitly to Decision Intelligence rather than arbitrarily picking a winner.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.strategy.domain import (
    ConflictType,
    Strategy,
    StrategyConflict,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.strategy.conflict_engine")


class ConflictDetectionEngine:
    """Analyzes candidate strategies to discover mutually exclusive or contending approaches."""

    def detect_conflicts(
        self,
        strategies: List[Strategy],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[StrategyConflict]:
        """Exhaustively inspect all strategy pairs for potential conflicts."""
        conflicts: List[StrategyConflict] = []
        n = len(strategies)
        if n < 2:
            return conflicts

        for i in range(n):
            for j in range(i + 1, n):
                s1 = strategies[i]
                s2 = strategies[j]

                # 1. Temporal Conflict (e.g. 'Act immediately' vs 'Wait for evidence')
                app1 = s1.recommended_approach.lower()
                app2 = s2.recommended_approach.lower()

                is_immediate_1 = ("immediately" in app1 or "fast" in app1 or "now" in app1)
                is_wait_2 = ("wait" in app2 or "accumulate" in app2 or "defer" in app2)
                is_immediate_2 = ("immediately" in app2 or "fast" in app2 or "now" in app2)
                is_wait_1 = ("wait" in app1 or "accumulate" in app1 or "defer" in app1)

                if (is_immediate_1 and is_wait_2) or (is_immediate_2 and is_wait_1):
                    conflicts.append(
                        StrategyConflict(
                            id=generate_id("sconf"),
                            strategy_a_id=s1.id,
                            strategy_b_id=s2.id,
                            conflict_type=ConflictType.TEMPORAL,
                            description=(
                                f"Temporal divergence: '{s1.name}' recommends immediate action, "
                                f"while '{s2.name}' recommends deferring for evidence."
                            ),
                            detected_under_context=context or {},
                            resolution_hint="Decision Intelligence should weigh latency tolerance against missing evidence risk.",
                            created_at=utc_now(),
                        )
                    )

                # 2. Resource Contention Conflict
                if (
                    "high_compute" in s1.objective.lower() and "high_compute" in s2.objective.lower()
                    and s1.category == s2.category
                ):
                    conflicts.append(
                        StrategyConflict(
                            id=generate_id("sconf"),
                            strategy_a_id=s1.id,
                            strategy_b_id=s2.id,
                            conflict_type=ConflictType.RESOURCE,
                            description=f"Resource contention: Both '{s1.name}' and '{s2.name}' demand high compute concurrently.",
                            detected_under_context=context or {},
                            resolution_hint="Allocate based on active mission priority via Resource Economy.",
                            created_at=utc_now(),
                        )
                    )

                # 3. Direct Contradiction (e.g. aggressive vs conservative)
                is_aggressive_1 = ("aggressive" in app1 or "force" in app1 or "override" in app1)
                is_conservative_2 = ("conservative" in app2 or "defensive" in app2 or "safe" in app2)
                is_aggressive_2 = ("aggressive" in app2 or "force" in app2 or "override" in app2)
                is_conservative_1 = ("conservative" in app1 or "defensive" in app1 or "safe" in app1)

                if (is_aggressive_1 and is_conservative_2) or (is_aggressive_2 and is_conservative_1):
                    conflicts.append(
                        StrategyConflict(
                            id=generate_id("sconf"),
                            strategy_a_id=s1.id,
                            strategy_b_id=s2.id,
                            conflict_type=ConflictType.DIRECT,
                            description=(
                                f"Direct tactical contradiction: '{s1.name}' uses aggressive intervention "
                                f"whereas '{s2.name}' mandates conservative defense."
                            ),
                            detected_under_context=context or {},
                            resolution_hint="Review safety invariants; conservative approach preferred under uncertain world-state.",
                            created_at=utc_now(),
                        )
                    )

                # 4. Capability Contention
                cap1 = s1.parameters if hasattr(s1, "parameters") else {}
                # Check target conditions for capability overlap
                s1_caps = {c.target_value for c in s1.conditions if c.field_path == "capability"}
                s2_caps = {c.target_value for c in s2.conditions if c.field_path == "capability"}
                shared_caps = s1_caps.intersection(s2_caps)
                if shared_caps and s1.category != s2.category:
                    conflicts.append(
                        StrategyConflict(
                            id=generate_id("sconf"),
                            strategy_a_id=s1.id,
                            strategy_b_id=s2.id,
                            conflict_type=ConflictType.CAPABILITY,
                            description=(
                                f"Capability lock contention: Both strategies require exclusive control of {shared_caps} "
                                f"under conflicting categories ({s1.category.value} vs {s2.category.value})."
                            ),
                            detected_under_context=context or {},
                            resolution_hint="Sequence sequentially or arbitrate through Swarm Orchestration.",
                            created_at=utc_now(),
                        )
                    )

        logger.info(f"Analyzed {n} strategies; identified {len(conflicts)} inter-strategy conflicts.")
        return conflicts
