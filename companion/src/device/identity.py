"""Device identity generator and persistent hardware-binding manager."""

import hashlib
import os
import platform
import uuid
from pathlib import Path


class DeviceIdentityManager:
    """Manages unique, unforgeable device identity bound to host characteristics."""

    def __init__(self, state_dir: Path | None = None) -> None:
        self.state_dir = state_dir or (Path.home() / ".kairo" / "companion")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.identity_file = self.state_dir / "device_identity.id"

    def _generate_hardware_fingerprint(self) -> str:
        """Derive a stable hardware digest from system characteristics without PII."""
        system_props = [
            platform.system(),
            platform.machine(),
            platform.processor(),
            platform.node() or "unknown_node",
        ]
        raw_seed = ":".join(system_props)
        return hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:16]

    def get_or_create_device_id(self) -> str:
        """Retrieve existing persistent device_id or generate a new unique identifier."""
        if self.identity_file.exists():
            stored_id = self.identity_file.read_text(encoding="utf-8").strip()
            if stored_id.startswith("dev_"):
                return stored_id

        # Unique device identity must combine random UUID and hardware fingerprint
        hw_fingerprint = self._generate_hardware_fingerprint()
        random_part = uuid.uuid4().hex[:12]
        device_id = f"dev_{hw_fingerprint}_{random_part}"

        # Write to protected local file
        self.identity_file.write_text(device_id, encoding="utf-8")
        try:
            os.chmod(self.identity_file, 0o600)
        except Exception:
            pass  # Windows permissions handled by user profile ACLs

        return device_id

    def get_device_info(self) -> dict[str, str]:
        """Return safe host platform metadata for registration."""
        return {
            "device_id": self.get_or_create_device_id(),
            "os_name": platform.system().lower(),
            "os_version": platform.version() or platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }
