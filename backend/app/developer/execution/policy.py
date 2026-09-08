"""Policy validator and allowlist checker for controlled test execution."""

import shlex
from typing import Sequence

DANGEROUS_SHELL_CHARS = {";", "&", "|", ">", "<", "`", "$", "\n", "\r"}


class CommandPolicyViolation(ValueError):
    """Raised when a proposed test command violates security policy."""


class TestCommandPolicy:
    """Enforces strict allowlisting for test command execution."""

    __test__ = False  # Prevent pytest from treating this class as a test suite

    def __init__(self, allowed_commands: Sequence[str] | None = None) -> None:
        self.allowed_commands = [c.strip() for c in (allowed_commands or []) if c.strip()]

    def validate_command(self, command_str: str) -> list[str]:
        """Validate that a requested command is in the exact allowlist and safe to run.

        SECURITY:
        - Must exactly match an item in allowed_commands (e.g. 'pytest' or 'npm test').
        - Prohibits shell meta-characters (&&, ||, ;, |, >, <, etc.).
        - Splits command safely into argv list without shell=True.
        """
        if not self.allowed_commands:
            raise CommandPolicyViolation(
                "No test commands are configured in KAIRO_ALLOWED_TEST_COMMANDS. Test execution is disabled."
            )

        if not command_str or not command_str.strip():
            raise CommandPolicyViolation("Test command cannot be empty.")

        clean_cmd = command_str.strip()

        # Check for shell metacharacters
        for ch in DANGEROUS_SHELL_CHARS:
            if ch in clean_cmd:
                raise CommandPolicyViolation(
                    f"Shell metacharacter '{ch}' is forbidden in test commands. Command composition is not permitted."
                )

        # Normalize and compare against allowlist
        if clean_cmd not in self.allowed_commands:
            raise CommandPolicyViolation(
                f"Command '{clean_cmd}' is not in the approved test allowlist: {self.allowed_commands}"
            )

        # Split into argv safely across platforms
        try:
            import sys
            norm_cmd = clean_cmd.replace("\\", "/") if sys.platform == "win32" else clean_cmd
            argv = shlex.split(norm_cmd)
        except ValueError as exc:
            raise CommandPolicyViolation(f"Invalid command syntax: {exc}") from exc

        if not argv:
            raise CommandPolicyViolation("Empty command argument list.")

        return argv
