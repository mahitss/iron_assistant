"""In-memory runtime registry for active AutonomousTaskEngine instances (Spec 1)."""

import logging
from typing import Dict, Optional
from app.tasks.engine import AutonomousTaskEngine

logger = logging.getLogger("kairo.tasks.registry")


class TaskEngineRegistry:
    """Registry maintaining active TaskEngine singleton and running task tracking."""

    def __init__(self) -> None:
        self._engine: Optional[AutonomousTaskEngine] = None
        self._active_tasks: dict[str, dict] = {}

    def get_engine(self) -> AutonomousTaskEngine:
        """Fetch or lazily initialize the AutonomousTaskEngine."""
        if self._engine is None:
            self._engine = AutonomousTaskEngine()
        return self._engine

    def set_engine(self, engine: AutonomousTaskEngine) -> None:
        """Explicitly inject an engine instance (for testing)."""
        self._engine = engine


# Global singleton
_registry_instance: Optional[TaskEngineRegistry] = None


def get_task_engine_registry() -> TaskEngineRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = TaskEngineRegistry()
    return _registry_instance


def get_task_engine() -> AutonomousTaskEngine:
    """Convenience getter for the global AutonomousTaskEngine."""
    return get_task_engine_registry().get_engine()
