"""Kairo Local Companion CLI and Daemon Entry Point."""

import argparse
import logging
import sys
from pathlib import Path

from companion.src.actions.executor import LocalActionExecutor
from companion.src.auth.credentials import LocalCredentialVault
from companion.src.auth.registration import DeviceRegistrationClient
from companion.src.device.identity import DeviceIdentityManager
from companion.src.device.state import CompanionState, DeviceStateManager
from companion.src.filesystem.sandbox import FilesystemSandbox
from companion.src.security.emergency_stop import LocalEmergencyStop
from companion.src.security.policy import LocalPolicyEngine
from companion.src.telemetry.logger import LocalAuditLogger
from companion.src.telemetry.reporter import TelemetryReporter
from companion.src.transport.client import CompanionTransportClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("kairo.companion.main")


class CompanionDaemon:
    """Core local runtime manager."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or (Path.home() / ".kairo" / "companion" / "companion.json")
        self.identity_mgr = DeviceIdentityManager()
        self.state_mgr = DeviceStateManager()
        self.emergency_stop = LocalEmergencyStop()
        self.vault = LocalCredentialVault()

        # Connect emergency stop to state reset
        self.emergency_stop.register_halt_callback(self.state_mgr.reset_to_safe_off)

        # Load allowed paths
        allowed_paths = [str(Path.home() / "KairoWorkspace")]
        self.sandbox = FilesystemSandbox(allowed_directories=allowed_paths)

        self.policy_engine = LocalPolicyEngine(
            state_manager=self.state_mgr,
            emergency_stop=self.emergency_stop,
            allowed_filesystem_paths=allowed_paths,
        )
        self.audit_logger = LocalAuditLogger()
        self.executor = LocalActionExecutor(
            identity_manager=self.identity_mgr,
            policy_engine=self.policy_engine,
            audit_logger=self.audit_logger,
            sandbox=self.sandbox,
        )
        self.transport = CompanionTransportClient(
            vault=self.vault,
            state_manager=self.state_mgr,
        )
        self.reporter = TelemetryReporter(
            identity_manager=self.identity_mgr,
            state_manager=self.state_mgr,
            transport_client=self.transport,
        )

    def print_status(self) -> None:
        """Display companion runtime status."""
        device_id = self.identity_mgr.get_or_create_device_id()
        creds = self.vault.load_credentials()
        info = self.identity_mgr.get_device_info()
        summary = self.state_mgr.get_status_summary()

        print("==================================================")
        print("KAIRO LOCAL COMPANION RUNTIME")
        print("==================================================")
        print(f"Device ID:         {device_id}")
        print(f"Platform:          {info['os_name']} ({info['architecture']})")
        print(f"State:             {summary['state']}")
        print(f"Emergency Stop:    {'ACTIVE (HALTED)' if self.emergency_stop.is_stopped else 'READY'}")
        print(f"Paired Status:     {'PAIRED (' + creds['cloud_url'] + ')' if creds else 'UNPAIRED'}")
        print("Capabilities:")
        for cap, en in summary["capabilities"].items():
            print(f"  - {cap:18s}: {'ON' if en else 'OFF'}")
        print("==================================================")


def main():
    parser = argparse.ArgumentParser(description="Kairo Local Companion Runtime")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    subparsers.add_parser("status", help="Print companion status and capability states")

    # stop (Emergency Stop)
    subparsers.add_parser("stop", help="Trigger Local Emergency Stop immediately")

    # reset-stop
    subparsers.add_parser("reset-stop", help="Reset Local Emergency Stop back to READY")

    # arm
    arm_parser = subparsers.add_parser("arm", help="Arm companion and enable specific capability")
    arm_parser.add_argument(
        "--capability", choices=["computer_control", "microphone", "camera", "filesystem"], required=True
    )

    # disarm
    subparsers.add_parser("disarm", help="Disarm companion and return to safe OFF state")

    # register
    reg_parser = subparsers.add_parser("register", help="Pair companion with Kairo Cloud")
    reg_parser.add_argument("--cloud-url", default="http://localhost:8000")
    reg_parser.add_argument("--token", required=True, help="User JWT authentication token")
    reg_parser.add_argument("--name", default="My PC", help="Friendly device name")

    args = parser.parse_args()
    daemon = CompanionDaemon()

    if args.command == "status" or not args.command:
        daemon.print_status()
    elif args.command == "stop":
        daemon.emergency_stop.trigger_stop("User executed CLI stop command")
        print("[EMERGENCY STOP] Local Emergency Stop is now ACTIVE. All capabilities halted.")
    elif args.command == "reset-stop":
        daemon.emergency_stop.reset_stop()
        print("[RESET] Emergency Stop cleared. Capabilities remain OFF until explicitly armed.")
    elif args.command == "arm":
        daemon.state_mgr.transition_to(CompanionState.ARMED, f"User armed capability {args.capability}")
        daemon.state_mgr.set_capability(args.capability, True)
        print(f"[ARMED] Capability '{args.capability}' enabled.")
    elif args.command == "disarm":
        daemon.state_mgr.reset_to_safe_off()
        print("[SAFE] Companion reset to safe OFF state. All capabilities disabled.")
    elif args.command == "register":
        client = DeviceRegistrationClient(
            cloud_base_url=args.cloud_url, vault=daemon.vault, identity_manager=daemon.identity_mgr
        )
        try:
            res = client.register(user_auth_token=args.token, device_name=args.name)
            print(f"[OK] Device paired successfully: {res['device_id']}")
        except Exception as e:
            print(f"[ERROR] Registration failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
