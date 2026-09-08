"""Controlled test execution runner."""

import asyncio
import logging
import time

from app.core.config import Settings, get_settings
from app.developer.execution.policy import CommandPolicyViolation, TestCommandPolicy
from app.developer.execution.sandbox import ExecutionSandbox
from app.developer.git.safety import redact_secrets
from app.developer.schemas import TestExecutionResult

logger = logging.getLogger("kairo.developer.execution.runner")


class TestRunner:
    """Safely runs approved test commands under strict policy and sandboxing."""

    __test__ = False  # Prevent pytest from treating this class as a test suite

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def run_test(
        self,
        repo_path: str,
        command: str,
        timeout_seconds: float = 30.0,
    ) -> TestExecutionResult:
        """Run an approved test command within an approved repository.

        SECURITY:
        - Never uses shell=True.
        - Only commands in KAIRO_ALLOWED_TEST_COMMANDS can execute.
        - Working directory strictly validated inside approved repository.
        - Subprocess stdout/stderr bounded and sanitized for secrets.
        - Enforces strict timeout with kill on expiration.
        """
        # 1. Validate repository and build sandbox
        sandbox = ExecutionSandbox.create_for_repo(
            repo_path=repo_path,
            timeout_seconds=timeout_seconds,
            settings=self.settings,
        )

        start_time = time.monotonic()
        try:
            # 2. Check command policy
            allowed_cmds = self.settings.get_allowed_test_commands()
            policy = TestCommandPolicy(allowed_commands=allowed_cmds)
            argv = policy.validate_command(command)
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(sandbox.repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=sandbox.timeout_seconds,
            )
            duration = time.monotonic() - start_time
            exit_code = proc.returncode or 0

            # Bound output
            max_b = sandbox.max_output_bytes
            stdout_str = stdout_bytes[:max_b].decode("utf-8", errors="replace")
            stderr_str = stderr_bytes[:max_b].decode("utf-8", errors="replace")

            if len(stdout_bytes) > max_b:
                stdout_str += f"\n\n[STDOUT TRUNCATED: Exceeded {max_b} bytes]"
            if len(stderr_bytes) > max_b:
                stderr_str += f"\n\n[STDERR TRUNCATED: Exceeded {max_b} bytes]"

            return TestExecutionResult(
                command=command,
                exit_code=exit_code,
                stdout=redact_secrets(stdout_str),
                stderr=redact_secrets(stderr_str),
                duration_seconds=round(duration, 3),
                status="success" if exit_code == 0 else "failure",
            )

        except asyncio.TimeoutError:
            duration = time.monotonic() - start_time
            try:
                proc.kill()
            except Exception:
                pass
            return TestExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {sandbox.timeout_seconds} seconds.",
                duration_seconds=round(duration, 3),
                status="timeout",
            )
        except CommandPolicyViolation as pol_err:
            duration = time.monotonic() - start_time
            return TestExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(pol_err),
                duration_seconds=round(duration, 3),
                status="rejected",
            )
        except Exception as exc:
            duration = time.monotonic() - start_time
            logger.error("Error executing test command '%s': %s", command, exc)
            return TestExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Process execution error: {exc}",
                duration_seconds=round(duration, 3),
                status="failure",
            )
