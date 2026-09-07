"""Safe, read-only system information tool."""

import platform
from typing import Any, Dict
from pydantic import BaseModel

from app.tools.base import BaseTool
from app.tools.permissions import PermissionLevel


class SystemInfoArgs(BaseModel):
    """Input arguments for the system info tool (no parameters required)."""
    pass


class SystemInfoTool(BaseTool):
    """Tool providing safe, high-level host platform and environment information."""

    name = "system_info"
    description = (
        "Retrieve safe, read-only operating system and runtime details "
        "(OS name, release version, architecture, and Python version). "
        "Does not expose environment variables, files, or sensitive credentials."
    )
    permission_level = PermissionLevel.READ
    args_model = SystemInfoArgs

    # Prohibited keys to ensure sensitive leaks never occur
    FORBIDDEN_KEYWORDS = {"env", "token", "key", "secret", "user", "pass", "cred", "path"}

    async def execute(self, **kwargs: Any) -> Dict[str, str]:
        """Collect safe system metadata."""
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }

    def verify(self, result: Any) -> bool:
        """Verify that the result contains only safe, non-sensitive metadata."""
        if not isinstance(result, dict):
            return False

        # Guard against forbidden keys
        for key in result.keys():
            if any(forbidden in key.lower() for forbidden in self.FORBIDDEN_KEYWORDS):
                return False

        required_keys = {"os", "os_release", "architecture", "python_version"}
        return required_keys.issubset(result.keys())
