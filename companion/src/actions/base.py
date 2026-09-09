"""Base class for all executable companion actions with timeout and parameter validation."""

import abc
import concurrent.futures
import logging
from typing import Any

logger = logging.getLogger("kairo.companion.actions.base")


class BaseCompanionAction(abc.ABC):
    """Abstract contract for allowlisted companion actions."""

    def __init__(self, name: str, default_timeout_seconds: float = 5.0) -> None:
        self.name = name
        self.default_timeout_seconds = default_timeout_seconds

    @abc.abstractmethod
    def run(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Subclass implementation of action execution logic."""
        raise NotImplementedError

    def execute_with_timeout(
        self, parameters: dict[str, Any], timeout: float | None = None
    ) -> dict[str, Any]:
        """Execute action within strict bounded timeout limit."""
        effective_timeout = timeout or self.default_timeout_seconds
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.run, parameters)
            try:
                result = future.result(timeout=effective_timeout)
                return {"success": True, "result": result}
            except concurrent.futures.TimeoutError as exc:
                logger.error("Action '%s' timed out after %.1fs", self.name, effective_timeout)
                raise TimeoutError(f"Action '{self.name}' timed out after {effective_timeout}s.") from exc
            except Exception as exc:
                logger.error("Action '%s' execution error: %s", self.name, exc)
                return {"success": False, "error": str(exc)}
