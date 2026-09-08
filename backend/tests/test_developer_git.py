"""Unit and integration tests for local Git inspection and safety."""

import subprocess
from pathlib import Path

import pytest

from app.core.config import Settings
from app.developer.git.diff import inspect_git_diff
from app.developer.git.history import inspect_git_branches, inspect_git_log
from app.developer.git.repository import LocalRepositoryRegistry
from app.developer.git.safety import PathSecurityError, validate_file_path, validate_repo_path
from app.developer.git.status import inspect_git_status


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Create a temporary initialized Git repository with sample commits and branches."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Configure git identity for commits
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "TestUser"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@kairo.internal"], cwd=repo, check=True, capture_output=True)

    # Initial commit
    file1 = repo / "hello.py"
    file1.write_text("print('hello world')\n", encoding="utf-8")
    subprocess.run(["git", "add", "hello.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)

    # Create a branch
    subprocess.run(["git", "branch", "feature-test"], cwd=repo, check=True, capture_output=True)

    return repo


@pytest.fixture
def developer_settings(tmp_path: Path):
    """Settings with tmp_path configured as approved repository root."""
    return Settings(
        KAIRO_DEVELOPER_ENABLED=True,
        KAIRO_REPOSITORY_ROOTS=str(tmp_path),
        KAIRO_MAX_GIT_LOG_ENTRIES=10,
        KAIRO_MAX_DIFF_CHARS=500,
    )


def test_validate_repo_path_approved_and_unapproved(temp_git_repo: Path, tmp_path: Path):
    """Ensure approved paths pass and unapproved paths or traversal attempts raise PathSecurityError."""
    approved_roots = [str(tmp_path)]

    # Valid
    validated = validate_repo_path(str(temp_git_repo), approved_roots)
    assert validated == temp_git_repo.resolve()

    # Traversal attempt
    with pytest.raises(PathSecurityError):
        validate_repo_path(str(temp_git_repo / ".." / ".." / "outside"), approved_roots)

    # Unapproved root
    with pytest.raises(PathSecurityError):
        validate_repo_path(str(temp_git_repo), ["/other/unapproved/root"])


def test_validate_file_path_security(temp_git_repo: Path):
    """Ensure path traversal, sensitive files, and device files are rejected."""
    # Valid file
    valid = validate_file_path(temp_git_repo, "hello.py")
    assert valid.name == "hello.py"

    # Traversal escape
    with pytest.raises(PathSecurityError):
        validate_file_path(temp_git_repo, "../../etc/passwd")

    # Sensitive .env file
    with pytest.raises(PathSecurityError):
        validate_file_path(temp_git_repo, ".env")

    # Sensitive key file
    with pytest.raises(PathSecurityError):
        validate_file_path(temp_git_repo, "id_rsa")


@pytest.mark.asyncio
async def test_git_status_clean_and_dirty(temp_git_repo: Path, developer_settings: Settings):
    """Verify clean state initially, then dirty state on modification and untracked file."""
    # Initially clean
    status = await inspect_git_status(str(temp_git_repo), settings=developer_settings)
    assert status.is_clean is True
    assert status.modified_files == []
    assert status.untracked_files == []

    # Modify file
    (temp_git_repo / "hello.py").write_text("print('modified')\n", encoding="utf-8")
    # Add untracked file
    (temp_git_repo / "new_file.txt").write_text("untracked\n", encoding="utf-8")

    status_dirty = await inspect_git_status(str(temp_git_repo), settings=developer_settings)
    assert status_dirty.is_clean is False
    assert "hello.py" in status_dirty.modified_files
    assert "new_file.txt" in status_dirty.untracked_files


@pytest.mark.asyncio
async def test_git_branches(temp_git_repo: Path, developer_settings: Settings):
    """Verify listing of local branches."""
    branches = await inspect_git_branches(str(temp_git_repo), settings=developer_settings)
    assert "feature-test" in branches.local_branches


@pytest.mark.asyncio
async def test_git_log_bounded(temp_git_repo: Path, developer_settings: Settings):
    """Verify commit log returns bounded commits with correct metadata."""
    # Add second commit
    (temp_git_repo / "second.py").write_text("# second\n", encoding="utf-8")
    subprocess.run(["git", "add", "second.py"], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], cwd=temp_git_repo, check=True, capture_output=True)

    commits = await inspect_git_log(str(temp_git_repo), limit=5, settings=developer_settings)
    assert len(commits) == 2
    assert commits[0].subject == "Second commit"
    assert commits[0].author == "TestUser"
    assert len(commits[0].sha) >= 7


@pytest.mark.asyncio
async def test_git_diff_working_tree_and_truncation(temp_git_repo: Path, developer_settings: Settings):
    """Verify working tree diff generation and truncation when exceeding limit."""
    # Write large diff
    large_content = "line\n" * 200
    (temp_git_repo / "hello.py").write_text(large_content, encoding="utf-8")

    diff_res = await inspect_git_diff(str(temp_git_repo), diff_type="working_tree", settings=developer_settings)
    assert diff_res.diff_type == "working_tree"
    assert len(diff_res.diff_content) > 0
    # Because limit is 500 chars, it should be marked as truncated
    assert diff_res.is_truncated is True
    assert "[DIFF TRUNCATED" in diff_res.diff_content


@pytest.mark.asyncio
async def test_local_repository_registry(temp_git_repo: Path, developer_settings: Settings):
    """Verify discovery of Git repositories under approved roots."""
    registry = LocalRepositoryRegistry(settings=developer_settings)
    repos = await registry.list_repositories()
    assert len(repos) >= 1
    assert any(r.name == "test_repo" for r in repos)

    info = await registry.get_repository_info(str(temp_git_repo))
    assert info.is_git is True
    assert info.name == "test_repo"
