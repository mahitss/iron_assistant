"""Pydantic data schemas for Kairo Developer and GitHub Intelligence System."""

from typing import Literal

from pydantic import BaseModel, Field


class RepoInfo(BaseModel):
    """Metadata describing a validated local repository."""

    name: str
    path: str
    is_git: bool = True
    current_branch: str | None = None
    remotes: list[str] = Field(default_factory=list)


class GitStatusResult(BaseModel):
    """Safe, structured output for repository working tree status."""

    repo_path: str
    branch: str = "HEAD"
    is_clean: bool = True
    staged_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)


class GitBranchInfo(BaseModel):
    """Listing of local and remote branches in repository."""

    current_branch: str
    local_branches: list[str] = Field(default_factory=list)
    remote_branches: list[str] = Field(default_factory=list)


class GitCommitInfo(BaseModel):
    """Safe bounded metadata for a Git commit."""

    sha: str
    author: str
    date: str
    subject: str


class GitDiffResult(BaseModel):
    """Bounded, sanitized diff content for working-tree, staged, or commit diff."""

    diff_type: Literal["working_tree", "staged", "commit"]
    target: str | None = None
    diff_content: str
    is_truncated: bool = False
    total_chars: int = 0


class CodeSearchMatch(BaseModel):
    """A single matching line in code search."""

    file_path: str
    line_number: int
    line_content: str


class CodeSearchResult(BaseModel):
    """Bounded results of a safe code search query."""

    query: str
    total_matches: int
    matches: list[CodeSearchMatch] = Field(default_factory=list)
    is_truncated: bool = False


class CodeFileContent(BaseModel):
    """Safely read text file content from an approved repository."""

    repo_path: str
    file_path: str
    content: str
    total_lines: int
    size_bytes: int
    is_truncated: bool = False


class TodoItem(BaseModel):
    """Detected TODO / FIXME marker in code."""

    marker: str
    file_path: str
    line_number: int
    text: str


class CodeAnalysisResult(BaseModel):
    """Deterministic, non-interpretive static analysis results."""

    repo_path: str
    languages: dict[str, int] = Field(default_factory=dict, description="File counts by extension")
    total_files: int = 0
    total_lines: int = 0
    todo_items: list[TodoItem] = Field(default_factory=list)
    syntax_valid: bool = True
    syntax_errors: list[str] = Field(default_factory=list)
    directory_structure: list[str] = Field(default_factory=list)


class GitHubRepoInfo(BaseModel):
    """Public safe metadata for a GitHub repository."""

    name: str
    full_name: str
    owner: str
    description: str | None = None
    visibility: str = "public"
    default_branch: str = "main"
    stars: int = 0
    forks: int = 0
    html_url: str = ""


class GitHubIssueInfo(BaseModel):
    """Bounded metadata for a GitHub issue."""

    number: int
    title: str
    state: str
    author: str
    created_at: str
    updated_at: str
    labels: list[str] = Field(default_factory=list)
    body: str = ""
    is_truncated: bool = False
    html_url: str = ""


class GitHubPRInfo(BaseModel):
    """Bounded metadata for a GitHub pull request."""

    number: int
    title: str
    state: str
    author: str
    source_branch: str
    target_branch: str
    created_at: str
    updated_at: str
    body: str = ""
    is_truncated: bool = False
    mergeable: bool | None = None
    html_url: str = ""


class GitHubCheckInfo(BaseModel):
    """Status metadata for a GitHub CI/Check run."""

    name: str
    status: str
    conclusion: str | None = None
    html_url: str = ""
    started_at: str | None = None
    completed_at: str | None = None


class TestExecutionResult(BaseModel):
    """Outcome of an approved test command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    status: Literal["success", "failure", "timeout", "rejected"]


class DeveloperContext(BaseModel):
    """Context block assembled for Kairo Core reasoning."""

    repo_name: str
    repo_path: str
    current_branch: str = "HEAD"
    status_summary: str = ""
    recent_commits: list[GitCommitInfo] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    relevant_diff: str | None = None
    test_summary: str | None = None
