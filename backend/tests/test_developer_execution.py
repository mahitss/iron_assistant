"""Unit tests for controlled test runner and execution sandboxing."""

import sys
from pathlib import Path

import pytest

from app.core.config import Settings
from app.developer.execution.policy import CommandPolicyViolation, TestCommandPolicy
from app.developer.execution.runner import TestRunner
from app.developer.git.safety import PathSecurityError
from app.tools.builtin.developer import TestRunnerTool
from app.tools.permissions import PermissionDecision, PermissionLevel, PermissionManager


@pytest.fixture
def repo_dir(tmp_path: Path):
    r = tmp_path / "app_repo"
    r.mkdir()
    return r


@pytest.fixture
def execution_settings(repo_dir: Path, tmp_path: Path):
    return Settings(
        KAIRO_DEVELOPER_ENABLED=True,
        KAIRO_REPOSITORY_ROOTS=str(tmp_path),
        KAIRO_ALLOWED_TEST_COMMANDS=f'{sys.executable} -c "print(\'tests passed\')",pytest,npm test',
    )


def test_command_policy_allowlist_and_dangerous_chars():
    """Verify exact allowlist checking and rejection of command chaining."""
    policy = TestCommandPolicy(allowed_commands=["pytest", "npm test"])

    # Approved command
    argv = policy.validate_command("pytest")
    assert argv == ["pytest"]

    argv_npm = policy.validate_command("npm test")
    assert argv_npm == ["npm", "test"]

    # Unapproved command
    with pytest.raises(CommandPolicyViolation):
        policy.validate_command("rm -rf /")

    # Command chaining / shell injection attempts
    with pytest.raises(CommandPolicyViolation):
        policy.validate_command("pytest && cat .env")

    with pytest.raises(CommandPolicyViolation):
        policy.validate_command("pytest; ls")

    with pytest.raises(CommandPolicyViolation):
        policy.validate_command("pytest | grep error")


def test_empty_allowlist_rejects_all():
    """Verify that an empty allowlist disables test execution entirely."""
    policy = TestCommandPolicy(allowed_commands=[])
    with pytest.raises(CommandPolicyViolation):
        policy.validate_command("pytest")


@pytest.mark.asyncio
async def test_runner_approved_command(repo_dir: Path, execution_settings: Settings):
    """Verify execution of an approved test command succeeds without shell=True."""
    runner = TestRunner(settings=execution_settings)
    approved_cmd = f'{sys.executable} -c "print(\'tests passed\')"'

    result = await runner.run_test(
        repo_path=str(repo_dir),
        command=approved_cmd,
    )
    assert result.status == "success"
    assert result.exit_code == 0
    assert "tests passed" in result.stdout


@pytest.mark.asyncio
async def test_runner_unapproved_command_rejected(repo_dir: Path, execution_settings: Settings):
    """Verify unapproved commands are rejected with status=rejected."""
    runner = TestRunner(settings=execution_settings)
    result = await runner.run_test(
        repo_path=str(repo_dir),
        command="python -m malicious_script",
    )
    assert result.status == "rejected"
    assert result.exit_code == -1


@pytest.mark.asyncio
async def test_runner_unapproved_repo_path(tmp_path: Path, execution_settings: Settings):
    """Verify executing tests outside approved repository roots raises PathSecurityError."""
    outside_dir = tmp_path / "outside" / "other"
    outside_dir.mkdir(parents=True)

    runner = TestRunner(settings=execution_settings)
    with pytest.raises(PathSecurityError):
        await runner.run_test(
            repo_path="/unapproved/system/dir",
            command="pytest",
        )


def test_test_runner_tool_permission_requires_approval():
    """Verify TestRunnerTool has EXECUTE permission and requires approval in PermissionManager."""
    tool = TestRunnerTool()
    assert tool.permission_level == PermissionLevel.EXECUTE

    pm = PermissionManager()
    decision = pm.evaluate(tool.name, tool.permission_level)
    assert decision == PermissionDecision.REQUIRES_APPROVAL
