"""Tests for Scoped Workspaces, Resource Locking, and Structured Diffs (Task 44)."""

import pytest
from app.agents.collaboration import (
    CollaborationCoordinator,
    ResourceLockConflictError,
)
from app.agents.workspace import (
    AgentWorkspace,
    CollaborativeArtifact,
    SharedTeamWorkspace,
)


def test_agent_workspace_isolation():
    ws = AgentWorkspace(
        agent_id="agent_coder",
        contract_id="ct_dev_1",
        project_id="proj_alpha",
        allowed_resources=["backend/app/auth/"],
    )

    ws.add_context_item("task_description", "Implement PBKDF2 hashing")
    assert ws.get_context_item("task_description") == "Implement PBKDF2 hashing"

    # Workspace restricts access outside allowed paths
    assert ws.can_access_resource("backend/app/auth/hash.py") is True
    assert ws.can_access_resource("backend/app/billing/charge.py") is False


def test_shared_workspace_artifact_versioning():
    shared = SharedTeamWorkspace(session_id="collab_session_1")

    art1 = CollaborativeArtifact(
        artifact_id="art_patch_01",
        title="Patch for Auth",
        creator_id="agent_coder",
        contract_id="ct_dev_1",
        content="diff --git a/auth.py",
        version=1,
    )
    shared.publish_artifact(art1)

    # Cannot silently overwrite existing artifact with identical version
    art1_dup = CollaborativeArtifact(
        artifact_id="art_patch_01",
        title="Overwriting Patch",
        creator_id="agent_rogue",
        contract_id="ct_dev_2",
        content="diff --git evil",
        version=1,
    )
    with pytest.raises(ValueError):
        shared.publish_artifact(art1_dup)

    # Publishing version 2 succeeds
    art2 = CollaborativeArtifact(
        artifact_id="art_patch_01",
        title="Patch for Auth v2",
        creator_id="agent_coder",
        contract_id="ct_dev_1",
        content="diff --git a/auth.py updated",
        version=2,
    )
    shared.publish_artifact(art2)
    latest = shared.get_latest_artifact("art_patch_01")
    assert latest.version == 2


def test_resource_locks_read_parallelism_and_write_serialization():
    coord = CollaborationCoordinator()

    # Multiple agents can acquire read leases concurrently
    lease1 = coord.acquire_read_lease("repo/src/core.py", "agent_reader_1")
    lease2 = coord.acquire_read_lease("repo/src/core.py", "agent_reader_2")
    assert lease1 is True
    assert lease2 is True

    # Agent attempting write lock while read leases are active is rejected
    with pytest.raises(ResourceLockConflictError):
        coord.acquire_write_lock("repo/src/core.py", "agent_writer")

    # Release read leases
    coord.release_read_lease("repo/src/core.py", "agent_reader_1")
    coord.release_read_lease("repo/src/core.py", "agent_reader_2")

    # Now write lock succeeds
    lock = coord.acquire_write_lock("repo/src/core.py", "agent_writer")
    assert lock is True

    # Second agent cannot acquire write lock simultaneously
    with pytest.raises(ResourceLockConflictError):
        coord.acquire_write_lock("repo/src/core.py", "agent_writer_2")

    coord.release_write_lock("repo/src/core.py", "agent_writer")


def test_structured_code_diff_merge_no_blind_concat():
    coord = CollaborationCoordinator()

    base_code = "def authenticate():\n    return False\n"
    diff_a = "def authenticate():\n    # Check token\n    return False\n"
    diff_b = "def authenticate():\n    return True\n"

    merged = coord.merge_code_diffs(base_code, diff_a, diff_b)
    assert "def authenticate():" in merged
    assert not merged.startswith(diff_a + diff_b)  # Ensures no blind concatenation
