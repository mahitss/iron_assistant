"""Tests for tool permissions and authorization policies."""

import pytest
from app.tools.permissions import (
    PermissionDecision,
    PermissionDeniedError,
    PermissionLevel,
    PermissionManager,
)


def test_default_permission_evaluations() -> None:
    """Ensure default permissions correctly categorize operations."""
    pm = PermissionManager()

    assert pm.evaluate("read_tool", PermissionLevel.READ) == PermissionDecision.AUTO_ALLOWED
    assert pm.evaluate("write_tool", PermissionLevel.WRITE) == PermissionDecision.REQUIRES_APPROVAL
    assert pm.evaluate("external_tool", PermissionLevel.EXTERNAL) == PermissionDecision.REQUIRES_APPROVAL
    assert pm.evaluate("destructive_tool", PermissionLevel.DESTRUCTIVE) == PermissionDecision.DENIED


def test_check_permission_read_succeeds() -> None:
    """Ensure READ level tools pass permission check without raising exceptions."""
    pm = PermissionManager()
    pm.check_permission("calculator", PermissionLevel.READ)


def test_check_permission_restricted_levels_raise_permission_denied() -> None:
    """Ensure restricted levels raise PermissionDeniedError by default."""
    pm = PermissionManager()

    with pytest.raises(PermissionDeniedError) as exc_write:
        pm.check_permission("file_writer", PermissionLevel.WRITE)
    assert "REQUIRES_APPROVAL" in exc_write.value.reason

    with pytest.raises(PermissionDeniedError) as exc_destructive:
        pm.check_permission("file_deleter", PermissionLevel.DESTRUCTIVE)
    assert "DENIED" in exc_destructive.value.reason
