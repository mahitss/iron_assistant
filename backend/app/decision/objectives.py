"""Objective management, weighting, source validation, and alignment scoring."""

from __future__ import annotations

from app.decision.safety import UnauthorizedObjectiveError
from app.decision.schemas import Objective

ALLOWED_OBJECTIVE_SOURCES = frozenset({
    "user_request",
    "goal_engine",
    "project_config",
    "policy",
    "system_default",
})

STANDARD_OBJECTIVES = {
    "RELIABILITY": {"direction": "MAXIMIZE", "default_priority": 1, "default_weight": 0.25},
    "SECURITY": {"direction": "MAXIMIZE", "default_priority": 1, "default_weight": 0.25},
    "COST": {"direction": "MINIMIZE", "default_priority": 2, "default_weight": 0.20},
    "LATENCY": {"direction": "MINIMIZE", "default_priority": 2, "default_weight": 0.15},
    "REVERSIBILITY": {"direction": "MAXIMIZE", "default_priority": 3, "default_weight": 0.15},
}


class ObjectiveManager:
    """Validates, normalizes, and evaluates objectives for decision options."""

    def validate_objectives(self, objectives: list[Objective]) -> list[Objective]:
        """Validates that objective sources are authorized and no injected objectives exist."""
        validated: list[Objective] = []
        for obj in objectives:
            src = obj.source.lower().strip()
            if src not in ALLOWED_OBJECTIVE_SOURCES:
                raise UnauthorizedObjectiveError(
                    f"Objective '{obj.name}' originates from unauthorized source '{obj.source}'. "
                    "External documents and untrusted text cannot dictate system objectives."
                )
            validated.append(obj)

        if not validated:
            # Fall back to standard core objectives
            for name, meta in STANDARD_OBJECTIVES.items():
                validated.append(
                    Objective(
                        name=name,
                        direction=meta["direction"],
                        priority=meta["default_priority"],
                        weight=meta["default_weight"],
                        source="system_default",
                    )
                )

        return self.normalize_weights(validated)

    def normalize_weights(self, objectives: list[Objective]) -> list[Objective]:
        """Normalizes objective weights to sum to 1.0."""
        total_weight = sum(obj.weight for obj in objectives)
        if total_weight <= 0.0:
            even_weight = 1.0 / max(1, len(objectives))
            for obj in objectives:
                obj.weight = round(even_weight, 3)
            return objectives

        for obj in objectives:
            obj.weight = round(obj.weight / total_weight, 3)
        return objectives

    def calculate_alignment(self, option_metrics: dict[str, float], objectives: list[Objective]) -> float:
        """Calculates weighted alignment score (0.0 to 1.0) of option metrics against objectives."""
        total_score = 0.0
        for obj in objectives:
            key = obj.name.lower()
            val = option_metrics.get(key, 0.5)

            # Score is bounded between 0.0 and 1.0
            if "MINIMIZE" in obj.direction.upper():
                # For minimization, lower values yield higher satisfaction
                score = max(0.0, min(1.0, 1.0 - (val / 100.0) if val > 1.0 else 1.0 - val))
            else:
                # For maximization, higher values yield higher satisfaction
                score = max(0.0, min(1.0, val / 100.0 if val > 1.0 else val))

            total_score += score * obj.weight

        return round(total_score, 3)

    def validate_and_normalize(self, objectives: list[Objective]) -> list[Objective]:
        """Validates sources and normalizes weights."""
        return self.validate_objectives(objectives)


objective_manager = ObjectiveManager()


