"""Repository Model and Git Authority integration (Task 54, Prompts #25-#27, #89)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class RepositoryModelManager:
    """Represents Git repositories with Git-provider as authoritative state."""

    @staticmethod
    def create_repository_node(
        repo_id: str,
        repo_full_name: str,  # e.g., "org/repo"
        default_branch: str = "main",
        current_commit: str = "HEAD",
        build_state: str = "SUCCESS",
        deployment_state: str = "DEPLOYED",
        is_clean: bool = True,
        scope_id: str | None = None,
        source: str = "github_api",
    ) -> EnvironmentNode:
        # Prompt #27: Git provider remains authoritative for repository state
        canonical = generate_canonical_id(NodeType.REPOSITORY, repo_full_name)
        meta = {
            "full_name": repo_full_name,
            "default_branch": default_branch,
            "current_commit": current_commit,
            "build_state": build_state,
            "deployment_state": deployment_state,
            "is_clean": is_clean,
            "authoritative_source": "git_provider",
        }
        return create_environment_node(
            node_id=f"repo_{repo_id}",
            node_type=NodeType.REPOSITORY,
            canonical_id=canonical,
            display_name=repo_full_name,
            metadata=meta,
            scope=ScopeType.PROJECT,
            scope_id=scope_id or repo_id,
            status=build_state,
            provenance={"source": source, "authoritative": True},
            confidence=1.0,
        )
