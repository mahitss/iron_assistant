"""Scenario loader, builder, and file serialization helpers."""

import json
from pathlib import Path
from typing import Any
from app.evaluation.schemas import EvaluationScenario, ScenarioCategory, GradingMethod, SecurityExpectations


class ScenarioLoader:
    """Loads and deserializes evaluation scenarios from files or directories."""

    @staticmethod
    def load_from_file(file_path: str | Path) -> list[EvaluationScenario]:
        """Load one or multiple scenarios from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return [EvaluationScenario.model_validate(item) for item in data]
        elif isinstance(data, dict):
            # Check if wrapped under "scenarios"
            if "scenarios" in data and isinstance(data["scenarios"], list):
                return [EvaluationScenario.model_validate(item) for item in data["scenarios"]]
            return [EvaluationScenario.model_validate(data)]
        else:
            raise ValueError(f"Invalid format in scenario file {path}: expected list or dict.")

    @classmethod
    def load_from_directory(cls, dir_path: str | Path) -> list[EvaluationScenario]:
        """Recursively load all scenario JSON files within a directory."""
        path = Path(dir_path)
        if not path.exists() or not path.is_dir():
            return []

        scenarios: list[EvaluationScenario] = []
        for file in path.glob("**/*.json"):
            try:
                scenarios.extend(cls.load_from_file(file))
            except Exception:
                continue
        return scenarios


class ScenarioBuilder:
    """Fluent builder for programmatically defining evaluation scenarios."""

    def __init__(
        self,
        scenario_id: str,
        name: str = "Untitled Scenario",
        category: ScenarioCategory = ScenarioCategory.CHAT,
    ) -> None:
        self._scenario = {
            "id": scenario_id,
            "name": name,
            "category": category,
            "input": "",
            "context": {},
            "expected_behavior": "",
            "allowed_tools": [],
            "forbidden_tools": [],
            "expected_output_properties": {},
            "security_expectations": SecurityExpectations().model_dump(),
            "timeout_seconds": 30.0,
            "grading_method": GradingMethod.DETERMINISTIC,
            "tags": [],
            "dataset_version": "v1.0.0",
            "is_holdout": False,
        }

    def with_name(self, name: str) -> "ScenarioBuilder":
        self._scenario["name"] = name
        return self

    def with_category(self, category: ScenarioCategory) -> "ScenarioBuilder":
        self._scenario["category"] = category
        return self

    def with_input(self, user_input: str | dict[str, Any]) -> "ScenarioBuilder":
        self._scenario["input"] = user_input
        return self

    def with_context(self, context: dict[str, Any]) -> "ScenarioBuilder":
        self._scenario["context"] = context
        return self

    def with_expected_behavior(self, behavior: str) -> "ScenarioBuilder":
        self._scenario["expected_behavior"] = behavior
        return self

    def with_allowed_tools(self, tools: list[str]) -> "ScenarioBuilder":
        self._scenario["allowed_tools"] = tools
        return self

    def with_forbidden_tools(self, tools: list[str]) -> "ScenarioBuilder":
        self._scenario["forbidden_tools"] = tools
        return self

    def with_security(self, **kwargs: Any) -> "ScenarioBuilder":
        self._scenario["security_expectations"].update(kwargs)
        return self

    def with_timeout(self, seconds: float) -> "ScenarioBuilder":
        self._scenario["timeout_seconds"] = seconds
        return self

    def with_grading_method(self, method: GradingMethod) -> "ScenarioBuilder":
        self._scenario["grading_method"] = method
        return self

    def with_tags(self, tags: list[str]) -> "ScenarioBuilder":
        self._scenario["tags"] = tags
        return self

    with_security_expectations = with_security
    with_grading = with_grading_method

    def build(self) -> EvaluationScenario:
        return EvaluationScenario.model_validate(self._scenario)
