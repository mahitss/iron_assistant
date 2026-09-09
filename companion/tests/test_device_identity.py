"""Tests for unique device identification, hardware fingerprinting, and credential vault."""

import shutil
import tempfile
from pathlib import Path

import pytest

from companion.src.auth.credentials import LocalCredentialVault
from companion.src.device.identity import DeviceIdentityManager


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


def test_device_identity_persistence_and_uniqueness(temp_dir):
    """Verify device_id is generated uniquely, starts with dev_, and persists across calls."""
    mgr = DeviceIdentityManager(state_dir=temp_dir)
    dev_id1 = mgr.get_or_create_device_id()
    assert dev_id1.startswith("dev_")

    # Calling again returns the exact same persistent ID
    dev_id2 = mgr.get_or_create_device_id()
    assert dev_id1 == dev_id2

    # Verify info dictionary
    info = mgr.get_device_info()
    assert info["device_id"] == dev_id1
    assert "os_name" in info
    assert "architecture" in info


def test_credential_vault_storage_and_purging(temp_dir):
    """Verify credentials can be stored, loaded, and safely purged."""
    vault = LocalCredentialVault(vault_dir=temp_dir)
    assert vault.load_credentials() is None

    creds = {"device_id": "dev_test_123", "device_token": "kairo_dtk_secret"}
    vault.store_credentials(creds)

    loaded = vault.load_credentials()
    assert loaded == creds

    # Clear vault
    vault.clear_credentials()
    assert vault.load_credentials() is None
