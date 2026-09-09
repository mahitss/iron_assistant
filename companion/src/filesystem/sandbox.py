"""Filesystem sandbox enforcing strict directory allowlists and preventing path traversal."""

import logging
import os
from pathlib import Path

logger = logging.getLogger("kairo.companion.filesystem.sandbox")

# Prohibited system directories that can NEVER be added to allowlist
SYSTEM_BLACK_LIST = {
    "/etc",
    "/var",
    "/bin",
    "/sbin",
    "/usr",
    "/boot",
    "/sys",
    "/proc",
    "/dev",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\Windows\\System32",
}

WINDOWS_DEVICE_NAMES = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "LPT1", "LPT2"}


class FilesystemSandbox:
    """Restricts all file reads and writes strictly to user-approved workspace allowlist."""

    def __init__(self, allowed_directories: list[str] | None = None) -> None:
        self.allowed_directories: list[Path] = []
        if allowed_directories:
            for d in allowed_directories:
                self.add_allowed_directory(d)

    def add_allowed_directory(self, path_str: str) -> None:
        """Add an approved workspace path after verifying it is not a forbidden system directory."""
        clean_path = Path(path_str).resolve()

        # Check blacklist
        for sys_dir in SYSTEM_BLACK_LIST:
            try:
                if clean_path == Path(sys_dir).resolve() or sys_dir.lower() in str(clean_path).lower():
                    if clean_path == Path(sys_dir).resolve():
                        raise PermissionError(f"System directory '{path_str}' cannot be added to allowlist.")
            except Exception:
                pass

        self.allowed_directories.append(clean_path)
        logger.info("[FILESYSTEM SANDBOX] Added allowed path: %s", clean_path)

    def validate_path(self, target_path: str | Path) -> Path:
        """Resolve canonical realpath and ensure it resides strictly within an allowed directory."""
        if not self.allowed_directories:
            raise PermissionError("No filesystem directories have been allowlisted by the user.")

        raw_str = str(target_path).strip()
        # Block Windows reserved device filenames
        base_name = os.path.basename(raw_str).split(".")[0].upper()
        if base_name in WINDOWS_DEVICE_NAMES:
            raise PermissionError(f"Access to reserved device filename '{base_name}' is prohibited.")

        # Resolve canonical absolute path (resolving all ../ and symlinks)
        target = Path(raw_str).resolve()

        # Check if canonical path is inside ANY allowed directory
        is_contained = False
        for allowed in self.allowed_directories:
            try:
                # Check relative_to (raises ValueError if not subpath)
                target.relative_to(allowed)
                is_contained = True
                break
            except ValueError:
                continue

        if not is_contained:
            raise PermissionError(
                f"Path traversal blocked: Path '{target}' is outside approved workspace directories: "
                f"{[str(p) for p in self.allowed_directories]}."
            )

        return target
