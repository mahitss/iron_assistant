"""Tests for filesystem sandbox, canonical path resolution, traversal defense, and file actions."""

import shutil
import tempfile
from pathlib import Path

import pytest

from companion.src.filesystem.operations import FilesystemAction
from companion.src.filesystem.sandbox import FilesystemSandbox


@pytest.fixture
def workspace_dirs():
    root = Path(tempfile.mkdtemp())
    workspace = root / "workspace"
    workspace.mkdir()
    forbidden = root / "forbidden"
    forbidden.mkdir()

    secret_file = forbidden / "secret.txt"
    secret_file.write_text("SUPER_SECRET_DATA", encoding="utf-8")

    yield {"workspace": workspace, "forbidden": forbidden, "root": root}
    shutil.rmtree(root, ignore_errors=True)


def test_sandbox_path_validation_and_traversal_blocking(workspace_dirs):
    """Verify canonical containment and traversal prevention."""
    sandbox = FilesystemSandbox(allowed_directories=[str(workspace_dirs["workspace"])])

    # 1. Valid subpath
    valid_target = workspace_dirs["workspace"] / "doc.txt"
    valid_target.write_text("Hello World", encoding="utf-8")
    assert sandbox.validate_path(str(valid_target)) == valid_target.resolve()

    # 2. Traversal attempt using ../
    traversal_attempt = str(workspace_dirs["workspace"] / ".." / "forbidden" / "secret.txt")
    with pytest.raises(PermissionError, match="Path traversal blocked"):
        sandbox.validate_path(traversal_attempt)

    # 3. Reserved device filename
    with pytest.raises(PermissionError, match="reserved device"):
        sandbox.validate_path(str(workspace_dirs["workspace"] / "NUL.txt"))


def test_sandboxed_read_write_delete(workspace_dirs):
    """Verify sandboxed file actions execute safely within boundaries."""
    sandbox = FilesystemSandbox(allowed_directories=[str(workspace_dirs["workspace"])])

    write_action = FilesystemAction("filesystem.write_restricted", sandbox)
    read_action = FilesystemAction("filesystem.read", sandbox)
    delete_action = FilesystemAction("filesystem.delete_restricted", sandbox)

    test_file = str(workspace_dirs["workspace"] / "notes.txt")

    # 1. Write file
    w_res = write_action.run({"path": test_file, "content": "Kairo Companion Notes"})
    assert w_res["success"] is True

    # 2. Read file
    r_res = read_action.run({"path": test_file})
    assert r_res["content"] == "Kairo Companion Notes"

    # 3. Delete file
    d_res = delete_action.run({"path": test_file})
    assert d_res["deleted"] is True
    assert not Path(test_file).exists()
