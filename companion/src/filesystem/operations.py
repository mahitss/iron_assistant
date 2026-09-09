"""Sandboxed filesystem operations with confirmation formatting and risk gating."""

import logging
from typing import Any

from companion.src.actions.base import BaseCompanionAction
from companion.src.filesystem.sandbox import FilesystemSandbox

logger = logging.getLogger("kairo.companion.filesystem.operations")


class FilesystemAction(BaseCompanionAction):
    """Executes sandboxed filesystem read, write, and delete operations."""

    MAX_READ_BYTES = 10 * 1024 * 1024  # 10 MB limit to prevent OOM

    def __init__(self, action_type: str, sandbox: FilesystemSandbox) -> None:
        super().__init__(name=action_type, default_timeout_seconds=5.0)
        self.action_type = action_type
        self.sandbox = sandbox

    def get_confirmation_details(self, parameters: dict[str, Any]) -> dict[str, str]:
        """Format human-readable confirmation for risky/destructive file actions."""
        target_str = str(parameters.get("path", ""))
        return {
            "file": target_str,
            "action": self.action_type,
            "reason": str(parameters.get("reason", "Operator requested file mutation")),
            "risk": "DESTRUCTIVE" if "delete" in self.action_type else "HIGH_RISK",
        }

    def run(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute sandboxed file operation."""
        path_str = parameters.get("path")
        if not path_str:
            raise ValueError("Parameter 'path' is required for filesystem operations.")

        # 1. Validate path containment inside sandbox
        canonical_path = self.sandbox.validate_path(path_str)

        # 2. Execute operation
        if self.action_type == "filesystem.read":
            if not canonical_path.exists():
                raise FileNotFoundError(f"File '{canonical_path}' does not exist.")
            if canonical_path.is_dir():
                raise IsADirectoryError(f"Path '{canonical_path}' is a directory, not a file.")

            file_size = canonical_path.stat().st_size
            if file_size > self.MAX_READ_BYTES:
                raise ValueError(
                    f"File size ({file_size} bytes) exceeds limit of {self.MAX_READ_BYTES} bytes."
                )

            content = canonical_path.read_text(encoding="utf-8", errors="replace")
            logger.info("[FILESYSTEM] Read %d bytes from %s", len(content), canonical_path)
            return {"path": str(canonical_path), "content": content, "size_bytes": file_size}

        elif self.action_type == "filesystem.write_restricted":
            content = parameters.get("content", "")
            canonical_path.parent.mkdir(parents=True, exist_ok=True)
            canonical_path.write_text(content, encoding="utf-8")
            logger.info("[FILESYSTEM] Wrote %d characters to %s", len(content), canonical_path)
            return {
                "path": str(canonical_path),
                "bytes_written": len(content.encode("utf-8")),
                "success": True,
            }

        elif self.action_type == "filesystem.delete_restricted":
            if not canonical_path.exists():
                raise FileNotFoundError(f"Cannot delete non-existent file '{canonical_path}'.")
            if canonical_path.is_dir():
                raise PermissionError("Directory deletion is not supported for security reasons.")

            canonical_path.unlink()
            logger.warning("[FILESYSTEM] DELETED file %s", canonical_path)
            return {"path": str(canonical_path), "deleted": True}

        raise NotImplementedError(f"Unsupported filesystem action: {self.action_type}")
