"""Device registration client for pairing companion runtime with Kairo Cloud."""

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from companion.src.auth.credentials import LocalCredentialVault
from companion.src.device.identity import DeviceIdentityManager

logger = logging.getLogger("kairo.companion.auth.registration")


class DeviceRegistrationClient:
    """Handles pairing handshake between Local Companion and Kairo Cloud."""

    def __init__(
        self,
        cloud_base_url: str = "http://localhost:8000",
        vault: LocalCredentialVault | None = None,
        identity_manager: DeviceIdentityManager | None = None,
    ) -> None:
        self.cloud_base_url = cloud_base_url.rstrip("/")
        self.vault = vault or LocalCredentialVault()
        self.identity_manager = identity_manager or DeviceIdentityManager()

    def register(
        self,
        user_auth_token: str,
        device_name: str = "My PC",
        allowed_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        """Perform pairing registration request against Kairo Cloud."""
        info = self.identity_manager.get_device_info()
        payload = {
            "device_id": info["device_id"],
            "device_name": device_name,
            "os_name": info["os_name"],
            "os_version": info["os_version"],
            "companion_version": "1.1.0",
            "allowed_paths": allowed_paths or [],
        }

        url = f"{self.cloud_base_url}/api/v1/devices/register"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {user_auth_token}",
                "X-User-ID": "default_user",
                "User-Agent": "Kairo-Companion/1.1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10.0) as response:
                body = json.loads(response.read().decode("utf-8"))
                credentials = {
                    "device_id": body["device_id"],
                    "device_token": body["device_token"],
                    "cloud_url": self.cloud_base_url,
                    "device_name": body["device_name"],
                    "status": body["status"],
                }
                self.vault.store_credentials(credentials)
                logger.info("Device paired successfully. ID: %s", body["device_id"])
                return body
        except urllib.error.HTTPError as exc:
            error_msg = exc.read().decode("utf-8", errors="ignore")
            logger.error("Registration failed HTTP %s: %s", exc.code, error_msg)
            raise RuntimeError(f"Registration failed HTTP {exc.code}: {error_msg}") from exc
        except Exception as exc:
            logger.error("Registration connection error: %s", exc)
            raise RuntimeError(f"Connection failed: {exc}") from exc
