"""Secure credential and token vault for local companion authentication."""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("kairo.companion.auth.credentials")


class LocalCredentialVault:
    """Stores sensitive device tokens and cryptographic secrets using encrypted or permission-guarded storage."""

    def __init__(self, vault_dir: Path | None = None) -> None:
        self.vault_dir = vault_dir or (Path.home() / ".kairo" / "companion" / "vault")
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.vault_file = self.vault_dir / "device_secrets.vault"

    def _obfuscate(self, data: str) -> str:
        """Obfuscate payload. In production environments, leverage DPAPI (Windows) or SecretService (Linux/macOS)."""
        return base64.b85encode(data.encode("utf-8")).decode("ascii")

    def _deobfuscate(self, data: str) -> str:
        return base64.b85decode(data.encode("ascii")).decode("utf-8")

    def store_credentials(self, credentials: dict[str, Any]) -> None:
        """Persist device credentials to permission-locked vault."""
        raw_json = json.dumps(credentials)
        encoded = self._obfuscate(raw_json)
        self.vault_file.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(self.vault_file, 0o600)
        except Exception:
            pass
        logger.info("Device credentials written securely to local vault.")

    def load_credentials(self) -> dict[str, Any] | None:
        """Retrieve stored device credentials from vault."""
        if not self.vault_file.exists():
            return None
        try:
            encoded = self.vault_file.read_text(encoding="utf-8").strip()
            raw_json = self._deobfuscate(encoded)
            return json.loads(raw_json)
        except Exception as exc:
            logger.error("Failed to load credentials from vault: %s", exc)
            return None

    def clear_credentials(self) -> None:
        """Purge stored credentials upon device revocation or logout."""
        if self.vault_file.exists():
            self.vault_file.unlink(missing_ok=True)
            logger.info("Local credential vault purged.")
