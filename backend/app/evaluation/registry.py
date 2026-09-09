"""In-memory registry for discovering, cataloging, and grouping evaluation scenarios."""

import logging
from pathlib import Path
from typing import Sequence
from app.evaluation.scenario import ScenarioLoader
from app.evaluation.schemas import EvaluationScenario, ScenarioCategory

logger = logging.getLogger("kairo.evaluation.registry")


class ScenarioRegistry:
    """Thread-safe catalog of testable evaluation scenarios."""

    SUITE_MAPPINGS: dict[str, list[ScenarioCategory]] = {
        "security": [ScenarioCategory.SECURITY, ScenarioCategory.COMPUTER],
        "routing": [ScenarioCategory.ROUTING],
        "tools": [ScenarioCategory.TOOLS, ScenarioCategory.GITHUB],
        "context": [ScenarioCategory.CONTEXT, ScenarioCategory.MEMORY, ScenarioCategory.PROJECTS],
        "memory": [ScenarioCategory.MEMORY],
        "knowledge": [ScenarioCategory.KNOWLEDGE],
        "research": [ScenarioCategory.RESEARCH, ScenarioCategory.BROWSER],
        "agents": [ScenarioCategory.AGENTS],
        "automation": [ScenarioCategory.AUTOMATION],
        "performance": [ScenarioCategory.PERFORMANCE, ScenarioCategory.RELIABILITY],
        "chat": [ScenarioCategory.CHAT],
    }

    def __init__(self, evals_dir: str | Path | None = None) -> None:
        self._scenarios: dict[str, EvaluationScenario] = {}
        self.evals_dir: Path | None = Path(evals_dir) if evals_dir else None

    def register(self, scenario: EvaluationScenario, allow_override: bool = True) -> None:
        """Register a single scenario."""
        if scenario.id in self._scenarios and not allow_override:
            raise ValueError(f"Scenario with ID '{scenario.id}' is already registered.")
        self._scenarios[scenario.id] = scenario

    def register_many(self, scenarios: Sequence[EvaluationScenario]) -> None:
        """Register multiple scenarios."""
        for s in scenarios:
            self.register(s)

    def get(self, scenario_id: str) -> EvaluationScenario | None:
        """Fetch scenario by exact ID."""
        return self._scenarios.get(scenario_id)

    def list_all(self, include_holdout: bool = False) -> list[EvaluationScenario]:
        """Return all registered scenarios."""
        if include_holdout:
            return list(self._scenarios.values())
        return [s for s in self._scenarios.values() if not s.is_holdout]

    def list_by_category(
        self, category: ScenarioCategory | str, include_holdout: bool = False
    ) -> list[EvaluationScenario]:
        """Filter scenarios by domain category."""
        cat_str = category.value if isinstance(category, ScenarioCategory) else str(category)
        return [
            s
            for s in self.list_all(include_holdout=include_holdout)
            if s.category.value == cat_str or s.category == category
        ]

    def list_by_suite(self, suite_name: str, include_holdout: bool = False) -> list[EvaluationScenario]:
        """Fetch all scenarios belonging to a designated test suite."""
        suite_clean = suite_name.lower().strip()
        if suite_clean in ("full", "all"):
            return self.list_all(include_holdout=include_holdout)

        categories = self.SUITE_MAPPINGS.get(suite_clean)
        if not categories:
            # Fallback check if suite name is a direct category
            try:
                cat = ScenarioCategory(suite_clean)
                return self.list_by_category(cat, include_holdout=include_holdout)
            except ValueError:
                return []

        return [
            s for s in self.list_all(include_holdout=include_holdout) if s.category in categories
        ]

    def list_suites(self) -> list[str]:
        """Return list of available suite names."""
        return ["full"] + list(self.SUITE_MAPPINGS.keys())

    def load_directory(self, dir_path: str | Path) -> int:
        """Auto-discover and load scenarios from directory."""
        loaded = ScenarioLoader.load_from_directory(dir_path)
        self.register_many(loaded)
        logger.info("Loaded %d scenarios into registry from %s", len(loaded), dir_path)
        return len(loaded)

    def load_all(self, dir_path: str | Path | None = None) -> int:
        """Auto-discover and load scenarios from evals_dir or specified path."""
        target = Path(dir_path) if dir_path else self.evals_dir
        if not target:
            raise ValueError("No directory path specified and evals_dir is not set.")
        return self.load_directory(target)

    # Convenience aliases
    get_by_category = list_by_category
    get_suite = list_by_suite

    def __len__(self) -> int:
        return len(self._scenarios)
