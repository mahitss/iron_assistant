"""Dependency Engine for Task 110:
Traverses and bounds dependency relationships between context elements to prevent graph explosion.

Supported Relationships:
- REQUIRES (e.g. decision outcome requires decision assumptions)
- SUPPORTS (evidence supports belief)
- DERIVED_FROM (derived concept points to source facts)
- EXPLAINS (causal chain explains anomaly)
- CONTRADICTS (competing claims)
- SUPERSEDES (newer state supersedes previous state)
- RELATED_TO (associative link)
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from app.context.working_set_domain import (
    ContextCandidate,
    ContextDependency,
    DependencyType,
    gen_ctx_id,
)


class DependencyEngine:
    """Manages bounded dependency graph expansion for context assembly."""

    MAX_EXPANSION_DEPTH = 3
    MAX_EXPANDED_ITEMS = 20

    @classmethod
    def resolve_dependencies(
        cls,
        seed_candidates: List[ContextCandidate],
        candidate_pool: Dict[str, ContextCandidate],
    ) -> Tuple[List[ContextCandidate], List[ContextDependency], bool]:
        """Traverse dependencies from seed candidates up to depth and count limits."""
        included_ids: Set[str] = {c.candidate_id for c in seed_candidates}
        result_candidates: List[ContextCandidate] = list(seed_candidates)
        discovered_dependencies: List[ContextDependency] = []
        truncated = False

        current_frontier = list(seed_candidates)
        depth = 0

        while current_frontier and depth < cls.MAX_EXPANSION_DEPTH:
            next_frontier: List[ContextCandidate] = []
            depth += 1

            for item in current_frontier:
                for dep_target_id in item.dependencies:
                    # Check if target candidate exists in the available candidate pool
                    target_cand = candidate_pool.get(dep_target_id)
                    if target_cand and target_cand.candidate_id not in included_ids:
                        if len(result_candidates) >= cls.MAX_EXPANDED_ITEMS + len(seed_candidates):
                            truncated = True
                            break

                        included_ids.add(target_cand.candidate_id)
                        result_candidates.append(target_cand)
                        next_frontier.append(target_cand)

                        # Create dependency trace
                        discovered_dependencies.append(
                            ContextDependency(
                                dependency_id=gen_ctx_id("cdep"),
                                source_item_id=item.candidate_id,
                                target_item_id=target_cand.candidate_id,
                                relationship=DependencyType.REQUIRES,
                                is_blocking=True,
                                explanation=f"Resolved dependency: {item.title} requires {target_cand.title}",
                            )
                        )

            if truncated:
                break
            current_frontier = next_frontier

        return result_candidates, discovered_dependencies, truncated
