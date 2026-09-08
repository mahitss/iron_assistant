"""DeveloperService orchestrating Git, GitHub, Code Search, Analysis, and Test execution."""

import logging
from typing import Literal

from app.core.config import Settings, get_settings
from app.developer.code.analysis import CodeAnalysisService
from app.developer.code.search import read_code_file, search_code_in_repository
from app.developer.execution.runner import TestRunner
from app.developer.git.diff import inspect_git_diff
from app.developer.git.history import inspect_git_branches, inspect_git_log
from app.developer.git.repository import LocalRepositoryRegistry
from app.developer.git.status import inspect_git_status
from app.developer.github.checks import get_github_checks
from app.developer.github.client import GitHubProvider
from app.developer.github.commits import list_github_commits
from app.developer.github.issues import get_github_issue, list_github_issues
from app.developer.github.pull_requests import (
    get_github_pull_request,
    get_github_pull_request_diff,
    list_github_pull_requests,
)
from app.developer.github.repositories import (
    get_github_repository,
    list_github_repositories,
)
from app.developer.schemas import (
    CodeAnalysisResult,
    CodeFileContent,
    CodeSearchResult,
    DeveloperContext,
    GitBranchInfo,
    GitCommitInfo,
    GitDiffResult,
    GitHubCheckInfo,
    GitHubIssueInfo,
    GitHubPRInfo,
    GitHubRepoInfo,
    GitStatusResult,
    RepoInfo,
    TestExecutionResult,
)

logger = logging.getLogger("kairo.developer.service")


class DeveloperService:
    """Unified developer intelligence service for Kairo."""

    def __init__(
        self,
        settings: Settings | None = None,
        github_provider: GitHubProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repo_registry = LocalRepositoryRegistry(settings=self.settings)
        self.github = github_provider or GitHubProvider(settings=self.settings)
        self.analysis = CodeAnalysisService(settings=self.settings)
        self.test_runner = TestRunner(settings=self.settings)

    # --- Local Git Operations ---

    async def list_local_repositories(self) -> list[RepoInfo]:
        """List discoverable Git repositories under approved roots."""
        return await self.repo_registry.list_repositories()

    async def get_local_repository(self, repo_path: str) -> RepoInfo:
        """Get validated info for a local repository."""
        return await self.repo_registry.get_repository_info(repo_path)

    async def get_git_status(self, repo_path: str) -> GitStatusResult:
        """Inspect working tree status of a repository."""
        return await inspect_git_status(repo_path, settings=self.settings)

    async def get_git_branches(self, repo_path: str) -> GitBranchInfo:
        """List local and remote branches in repository."""
        return await inspect_git_branches(repo_path, settings=self.settings)

    async def get_git_log(self, repo_path: str, limit: int = 10) -> list[GitCommitInfo]:
        """Inspect recent commit history."""
        return await inspect_git_log(repo_path, limit=limit, settings=self.settings)

    async def get_git_diff(
        self,
        repo_path: str,
        diff_type: Literal["working_tree", "staged", "commit"] = "working_tree",
        target: str | None = None,
    ) -> GitDiffResult:
        """Inspect bounded diff content."""
        return await inspect_git_diff(
            repo_path=repo_path,
            diff_type=diff_type,
            target=target,
            settings=self.settings,
        )

    # --- Code Search & Reading ---

    def search_code(
        self,
        repo_path: str,
        query: str,
        path: str | None = None,
    ) -> CodeSearchResult:
        """Search code within an approved repository."""
        return search_code_in_repository(
            repo_path=repo_path,
            query=query,
            sub_path=path,
            settings=self.settings,
        )

    def read_file(
        self,
        repo_path: str,
        file_path: str,
        max_lines: int = 1000,
    ) -> CodeFileContent:
        """Safely read text file content."""
        return read_code_file(
            repo_path=repo_path,
            file_path=file_path,
            max_lines=max_lines,
            settings=self.settings,
        )

    def analyze_code(self, repo_path: str) -> CodeAnalysisResult:
        """Run deterministic static analysis."""
        return self.analysis.analyze_repository(repo_path=repo_path)

    # --- GitHub Operations ---

    async def list_github_repositories(self, limit: int = 20) -> list[GitHubRepoInfo]:
        """List accessible GitHub repositories."""
        return await list_github_repositories(self.github, limit=limit)

    async def get_github_repository(self, owner: str, repo: str) -> GitHubRepoInfo:
        """Get metadata for a GitHub repository."""
        return await get_github_repository(self.github, owner=owner, repo=repo)

    async def list_github_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 20,
    ) -> list[GitHubIssueInfo]:
        """List issues for a repository."""
        return await list_github_issues(self.github, owner=owner, repo=repo, state=state, limit=limit)

    async def get_github_issue(self, owner: str, repo: str, number: int) -> GitHubIssueInfo:
        """Get details for a specific issue."""
        return await get_github_issue(self.github, owner=owner, repo=repo, number=number)

    async def list_github_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 20,
    ) -> list[GitHubPRInfo]:
        """List pull requests for a repository."""
        return await list_github_pull_requests(self.github, owner=owner, repo=repo, state=state, limit=limit)

    async def get_github_pull_request(self, owner: str, repo: str, number: int) -> GitHubPRInfo:
        """Get details for a specific pull request."""
        return await get_github_pull_request(self.github, owner=owner, repo=repo, number=number)

    async def get_github_pull_request_diff(self, owner: str, repo: str, number: int) -> GitDiffResult:
        """Get unified diff for a pull request."""
        return await get_github_pull_request_diff(
            self.github,
            owner=owner,
            repo=repo,
            number=number,
            max_chars=self.settings.KAIRO_MAX_DIFF_CHARS,
        )

    async def list_github_commits(self, owner: str, repo: str, limit: int = 20) -> list[GitCommitInfo]:
        """List commits for a repository."""
        return await list_github_commits(self.github, owner=owner, repo=repo, limit=limit)

    async def get_github_checks(self, owner: str, repo: str, ref: str = "main") -> list[GitHubCheckInfo]:
        """Get CI checks status for a commit or branch."""
        return await get_github_checks(self.github, owner=owner, repo=repo, ref=ref)

    # --- Test Execution ---

    async def run_approved_test(
        self,
        repo_path: str,
        command: str,
        timeout_seconds: float = 30.0,
    ) -> TestExecutionResult:
        """Execute an approved test command through the controlled test runner."""
        return await self.test_runner.run_test(
            repo_path=repo_path,
            command=command,
            timeout_seconds=timeout_seconds,
        )

    # --- Context Construction ---

    async def build_developer_context(self, repo_path: str) -> DeveloperContext:
        """Construct bounded developer context for Kairo Core reasoning."""
        info = await self.get_local_repository(repo_path)
        status = await self.get_git_status(repo_path)
        commits = await self.get_git_log(repo_path, limit=5)

        status_parts = []
        if status.is_clean:
            status_parts.append("working tree clean")
        else:
            if status.modified_files:
                status_parts.append(f"{len(status.modified_files)} modified")
            if status.staged_files:
                status_parts.append(f"{len(status.staged_files)} staged")
            if status.untracked_files:
                status_parts.append(f"{len(status.untracked_files)} untracked")

        return DeveloperContext(
            repo_name=info.name,
            repo_path=info.path,
            current_branch=status.branch,
            status_summary=", ".join(status_parts) or "clean",
            recent_commits=commits,
            relevant_files=(status.modified_files + status.staged_files)[:10],
        )
