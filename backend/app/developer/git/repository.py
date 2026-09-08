"""Local Git repository registry and safe discovery."""

import asyncio
import logging
from pathlib import Path

from app.core.config import Settings, get_settings
from app.developer.git.safety import validate_repo_path
from app.developer.schemas import RepoInfo

logger = logging.getLogger("kairo.developer.git.repo")


async def run_git_exec(args: list[str], cwd: Path, timeout: float = 10.0) -> tuple[int, str, str]:
    """Execute git with strict argument separation and no shell expansion.

    SECURITY:
    - Never uses shell=True.
    - Runs directly via asyncio.create_subprocess_exec.
    - Enforces strict timeout and working directory validation.
    """
    cmd = ["git"] + args
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "", "Git command timed out"
    except FileNotFoundError:
        return -1, "", "git executable not found in PATH"
    except Exception as exc:
        return -1, "", f"Git execution error: {exc}"


class LocalRepositoryRegistry:
    """Registry and discovery service for local Git repositories."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def approved_roots(self) -> list[str]:
        return self.settings.get_approved_repo_roots()

    async def get_repository_info(self, repo_path: str) -> RepoInfo:
        """Validate and return safe metadata for a local repository."""
        validated_path = validate_repo_path(repo_path, self.approved_roots)

        # Verify .git exists or git rev-parse succeeds
        code, branch_out, _ = await run_git_exec(["rev-parse", "--abbrev-ref", "HEAD"], cwd=validated_path)
        is_git = (code == 0) or (validated_path / ".git").exists()
        current_branch = branch_out.strip() if code == 0 else None

        # Fetch remotes
        remotes: list[str] = []
        if is_git:
            code_remotes, remotes_out, _ = await run_git_exec(["remote", "-v"], cwd=validated_path)
            if code_remotes == 0 and remotes_out:
                for line in remotes_out.strip().splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] not in remotes:
                        remotes.append(parts[0])

        return RepoInfo(
            name=validated_path.name,
            path=str(validated_path),
            is_git=is_git,
            current_branch=current_branch,
            remotes=remotes,
        )

    async def list_repositories(self, max_depth: int = 2) -> list[RepoInfo]:
        """Discover approved Git repositories within configured roots."""
        results: list[RepoInfo] = []
        roots = self.approved_roots
        if not roots:
            return results

        for root_str in roots:
            root_path = Path(root_str)
            if not root_path.exists() or not root_path.is_dir():
                continue

            # Check if root itself is a git repo
            if (root_path / ".git").exists():
                try:
                    info = await self.get_repository_info(str(root_path))
                    results.append(info)
                    continue
                except Exception:
                    pass

            # Search immediate subdirectories
            try:
                for entry in root_path.iterdir():
                    if entry.is_dir() and not entry.name.startswith("."):
                        if (entry / ".git").exists():
                            try:
                                info = await self.get_repository_info(str(entry))
                                results.append(info)
                            except Exception:
                                pass
            except (PermissionError, OSError) as exc:
                logger.warning("Could not traverse directory %s: %s", root_path, exc)

        return results
