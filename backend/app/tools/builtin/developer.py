"""Developer tools for repository inspection, code search, GitHub, and controlled testing."""

from typing import Literal

from pydantic import BaseModel, Field

from app.developer.service import DeveloperService
from app.tools.base import BaseTool
from app.tools.permissions import PermissionLevel
from app.tools.schemas import ToolResult

_GLOBAL_DEVELOPER_SERVICE: DeveloperService | None = None


def get_developer_service() -> DeveloperService:
    """Provide singleton DeveloperService instance."""
    global _GLOBAL_DEVELOPER_SERVICE
    if _GLOBAL_DEVELOPER_SERVICE is None:
        _GLOBAL_DEVELOPER_SERVICE = DeveloperService()
    return _GLOBAL_DEVELOPER_SERVICE


def set_developer_service(service: DeveloperService | None) -> None:
    """Set or override singleton DeveloperService instance (for testing)."""
    global _GLOBAL_DEVELOPER_SERVICE
    _GLOBAL_DEVELOPER_SERVICE = service


# ==========================================
# 1. Git Status Tool
# ==========================================

class GitStatusArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Inspect the working tree status (clean/dirty, staged, modified, untracked) of an approved Git repository."
    permission_level = PermissionLevel.READ
    args_model = GitStatusArgs

    async def execute(self, args: GitStatusArgs) -> ToolResult:
        service = get_developer_service()
        try:
            status = await service.get_git_status(args.repo_path)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=status.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 2. Git Branches Tool
# ==========================================

class GitBranchesArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")


class GitBranchesTool(BaseTool):
    name = "git_branches"
    description = "List the current branch, local branches, and remote branches of an approved Git repository."
    permission_level = PermissionLevel.READ
    args_model = GitBranchesArgs

    async def execute(self, args: GitBranchesArgs) -> ToolResult:
        service = get_developer_service()
        try:
            branches = await service.get_git_branches(args.repo_path)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=branches.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 3. Git Log Tool
# ==========================================

class GitLogArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")
    limit: int = Field(default=10, description="Max number of commits to retrieve (bounded up to 50)")


class GitLogTool(BaseTool):
    name = "git_log"
    description = "Inspect bounded recent commit history (SHA, author, date, subject) for an approved Git repository."
    permission_level = PermissionLevel.READ
    args_model = GitLogArgs

    async def execute(self, args: GitLogArgs) -> ToolResult:
        service = get_developer_service()
        try:
            commits = await service.get_git_log(args.repo_path, limit=args.limit)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=[c.model_dump() for c in commits],
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 4. Git Diff Tool
# ==========================================

class GitDiffArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")
    diff_type: Literal["working_tree", "staged", "commit"] = Field(
        default="working_tree",
        description="Type of diff to inspect: working_tree, staged, or commit",
    )
    target: str | None = Field(
        default=None,
        description="Optional target file path (for working_tree) or commit SHA/ref (for commit diff)",
    )


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Inspect bounded unified diff content for working tree, staged changes, or a specific commit in an approved repository."
    permission_level = PermissionLevel.READ
    args_model = GitDiffArgs

    async def execute(self, args: GitDiffArgs) -> ToolResult:
        service = get_developer_service()
        try:
            diff_res = await service.get_git_diff(
                repo_path=args.repo_path,
                diff_type=args.diff_type,
                target=args.target,
            )
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=diff_res.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 5. Code Search Tool
# ==========================================

class CodeSearchArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")
    query: str = Field(..., description="Text query or token to search for")
    path: str | None = Field(default=None, description="Optional subdirectory or file path to restrict search")


class CodeSearchTool(BaseTool):
    name = "code_search"
    description = "Search for text or tokens across source code files in an approved repository (excludes .git, node_modules, and secrets)."
    permission_level = PermissionLevel.READ
    args_model = CodeSearchArgs

    async def execute(self, args: CodeSearchArgs) -> ToolResult:
        service = get_developer_service()
        try:
            search_res = service.search_code(
                repo_path=args.repo_path,
                query=args.query,
                path=args.path,
            )
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=search_res.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 6. Code Read File Tool
# ==========================================

class CodeReadFileArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")
    file_path: str = Field(..., description="Relative path of text file to read inside repository")
    max_lines: int = Field(default=1000, description="Maximum lines of content to read")


class CodeReadFileTool(BaseTool):
    name = "code_read_file"
    description = "Read text file contents from an approved repository with path traversal protection, binary rejection, and secret redaction."
    permission_level = PermissionLevel.READ
    args_model = CodeReadFileArgs

    async def execute(self, args: CodeReadFileArgs) -> ToolResult:
        service = get_developer_service()
        try:
            file_res = service.read_file(
                repo_path=args.repo_path,
                file_path=args.file_path,
                max_lines=args.max_lines,
            )
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=file_res.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 7. Code Analysis Tool
# ==========================================

class CodeAnalysisArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")


class CodeAnalysisTool(BaseTool):
    name = "code_analyze"
    description = "Run deterministic static analysis (language breakdown, line counts, TODO/FIXME markers, Python AST syntax validation)."
    permission_level = PermissionLevel.READ
    args_model = CodeAnalysisArgs

    async def execute(self, args: CodeAnalysisArgs) -> ToolResult:
        service = get_developer_service()
        try:
            analysis_res = service.analyze_code(args.repo_path)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=analysis_res.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 8. GitHub Repositories Tools
# ==========================================

class GitHubListReposArgs(BaseModel):
    limit: int = Field(default=20, description="Maximum number of repositories to list")


class GitHubListRepositoriesTool(BaseTool):
    name = "github_list_repositories"
    description = "List accessible GitHub repositories with safe public metadata."
    permission_level = PermissionLevel.READ
    args_model = GitHubListReposArgs

    async def execute(self, args: GitHubListReposArgs) -> ToolResult:
        service = get_developer_service()
        try:
            repos = await service.list_github_repositories(limit=args.limit)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=[r.model_dump() for r in repos],
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


class GitHubGetRepoArgs(BaseModel):
    owner: str = Field(..., description="Repository owner/organization")
    repo: str = Field(..., description="Repository name")


class GitHubGetRepositoryTool(BaseTool):
    name = "github_get_repository"
    description = "Get safe metadata for a specific GitHub repository."
    permission_level = PermissionLevel.READ
    args_model = GitHubGetRepoArgs

    async def execute(self, args: GitHubGetRepoArgs) -> ToolResult:
        service = get_developer_service()
        try:
            info = await service.get_github_repository(args.owner, args.repo)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=info.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 9. GitHub Issues Tools
# ==========================================

class GitHubListIssuesArgs(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    state: Literal["open", "closed", "all"] = Field(default="open", description="Issue state filter")
    limit: int = Field(default=20, description="Max issues to return")


class GitHubListIssuesTool(BaseTool):
    name = "github_list_issues"
    description = "List issues for a GitHub repository with safe, bounded body content."
    permission_level = PermissionLevel.READ
    args_model = GitHubListIssuesArgs

    async def execute(self, args: GitHubListIssuesArgs) -> ToolResult:
        service = get_developer_service()
        try:
            issues = await service.list_github_issues(
                owner=args.owner,
                repo=args.repo,
                state=args.state,
                limit=args.limit,
            )
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=[i.model_dump() for i in issues],
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


class GitHubGetIssueArgs(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    number: int = Field(..., description="Issue number")


class GitHubGetIssueTool(BaseTool):
    name = "github_get_issue"
    description = "Get details and bounded body of a specific GitHub issue."
    permission_level = PermissionLevel.READ
    args_model = GitHubGetIssueArgs

    async def execute(self, args: GitHubGetIssueArgs) -> ToolResult:
        service = get_developer_service()
        try:
            issue = await service.get_github_issue(args.owner, args.repo, args.number)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=issue.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 10. GitHub Pull Requests Tools
# ==========================================

class GitHubListPRsArgs(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    state: Literal["open", "closed", "all"] = Field(default="open", description="Pull request state filter")
    limit: int = Field(default=20, description="Max pull requests to return")


class GitHubListPullRequestsTool(BaseTool):
    name = "github_list_pull_requests"
    description = "List pull requests in a GitHub repository."
    permission_level = PermissionLevel.READ
    args_model = GitHubListPRsArgs

    async def execute(self, args: GitHubListPRsArgs) -> ToolResult:
        service = get_developer_service()
        try:
            prs = await service.list_github_pull_requests(
                owner=args.owner,
                repo=args.repo,
                state=args.state,
                limit=args.limit,
            )
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=[p.model_dump() for p in prs],
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


class GitHubGetPRArgs(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    number: int = Field(..., description="Pull request number")


class GitHubGetPullRequestTool(BaseTool):
    name = "github_get_pull_request"
    description = "Get details and bounded body of a specific GitHub pull request."
    permission_level = PermissionLevel.READ
    args_model = GitHubGetPRArgs

    async def execute(self, args: GitHubGetPRArgs) -> ToolResult:
        service = get_developer_service()
        try:
            pr = await service.get_github_pull_request(args.owner, args.repo, args.number)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=pr.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


class GitHubGetPRDiffArgs(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    number: int = Field(..., description="Pull request number")


class GitHubGetPullRequestDiffTool(BaseTool):
    name = "github_get_pull_request_diff"
    description = "Inspect bounded unified diff content for a GitHub pull request with secret redaction."
    permission_level = PermissionLevel.READ
    args_model = GitHubGetPRDiffArgs

    async def execute(self, args: GitHubGetPRDiffArgs) -> ToolResult:
        service = get_developer_service()
        try:
            diff_res = await service.get_github_pull_request_diff(args.owner, args.repo, args.number)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=diff_res.model_dump(),
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 11. GitHub CI / Checks Tool
# ==========================================

class GitHubGetChecksArgs(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    ref: str = Field(default="main", description="Commit SHA or branch name to inspect")


class GitHubGetChecksTool(BaseTool):
    name = "github_get_checks"
    description = "Inspect CI check runs and workflow status for a commit or branch on GitHub."
    permission_level = PermissionLevel.READ
    args_model = GitHubGetChecksArgs

    async def execute(self, args: GitHubGetChecksArgs) -> ToolResult:
        service = get_developer_service()
        try:
            checks = await service.get_github_checks(args.owner, args.repo, ref=args.ref)
            return ToolResult(
                success=True,
                tool_name=self.name,
                result=[c.model_dump() for c in checks],
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )


# ==========================================
# 12. Controlled Test Runner Tool
# ==========================================

class TestRunnerArgs(BaseModel):
    repo_path: str = Field(..., description="Path to the approved local Git repository")
    command: str = Field(..., description="Exact test command to run (must be approved in KAIRO_ALLOWED_TEST_COMMANDS)")


class TestRunnerTool(BaseTool):
    name = "test_runner"
    description = (
        "Execute an approved test command (e.g. 'pytest', 'npm test') under strict sandboxing. "
        "Requires explicit user approval and must match KAIRO_ALLOWED_TEST_COMMANDS."
    )
    permission_level = PermissionLevel.EXECUTE
    args_model = TestRunnerArgs

    async def execute(self, args: TestRunnerArgs) -> ToolResult:
        service = get_developer_service()
        try:
            res = await service.run_approved_test(
                repo_path=args.repo_path,
                command=args.command,
            )
            return ToolResult(
                success=(res.status == "success"),
                tool_name=self.name,
                result=res.model_dump(),
                error=res.stderr if res.status != "success" else None,
                verification_status="verified",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(exc),
                verification_status="failed",
            )
