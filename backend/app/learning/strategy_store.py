"""In-memory and versioned strategy store for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
from typing import Any

from app.learning.strategies import Strategy, StrategyStatus

logger = logging.getLogger("kairo.learning.strategy_store")


class StrategyStore:
    """Manages active, candidate, and versioned strategies."""

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._versions: dict[str, list[Strategy]] = {}  # strategy_id -> list of versions

    def save(self, strategy: Strategy) -> None:
        """Store or update a strategy, keeping track of versions."""
        sid = strategy.strategy_id
        if sid in self._strategies:
            # Preserve previous version in history
            history = self._versions.setdefault(sid, [])
            history.append(self._strategies[sid].model_copy(deep=True))

        self._strategies[sid] = strategy

    def get(self, strategy_id: str) -> Strategy | None:
        """Retrieve strategy by ID."""
        return self._strategies.get(strategy_id)

    def list_strategies(
        self,
        domain: str | None = None,
        status: StrategyStatus | None = None,
        project_id: str | None = None,
    ) -> list[Strategy]:
        """Query strategies matching domain, status, or project scope."""
        results = list(self._strategies.values())

        if domain:
            clean_domain = domain.strip().lower()
            results = [s for s in results if s.domain.strip().lower() == clean_domain]

        if status:
            results = [s for s in results if s.status == status]

        if project_id:
            results = [
                s for s in results
                if not s.scope.get("project_id") or s.scope.get("project_id") == project_id
            ]

        return results

    def get_history(self, strategy_id: str) -> list[Strategy]:
        """Retrieve historical revisions of a strategy."""
        return list(self._versions.get(strategy_id, []))
