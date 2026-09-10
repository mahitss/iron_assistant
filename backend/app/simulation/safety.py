"""Safety firewall, isolation guards, and security boundaries for Kairo Simulation Engine.

Enforces:
1. Zero production side effects from simulation APIs.
2. Hard separation between simulation and production ToolExecutor.
3. Secret and credential scrubbing.
4. Prompt injection and tool-injection sanitization.
5. Strict SIMULATION_ONLY and is_hypothetical tagging.
"""

from __future__ import annotations

import re
from typing import Any


class SimulationSafetyError(Exception):
    """Base exception for simulation safety violations."""
    pass


class SimulationSideEffectError(SimulationSafetyError):
    """Raised when a simulation process attempts to execute a real-world side effect."""
    pass


class ProductionMutationBlockedError(SimulationSafetyError):
    """Raised when an operation targets production resources from within a simulation context."""
    pass


class UnverifiedExecutionError(SimulationSafetyError):
    """Raised when an attempt is made to execute a simulation plan without passing ExecutionGate."""
    pass


class StaleSimulationError(SimulationSafetyError):
    """Raised when attempting to transition a stale or invalidated simulation plan to real execution."""
    pass


class SimulationResourceBudgetExceededError(SimulationSafetyError):
    """Raised when simulation compute exceeds memory, depth, or iteration bounds."""
    pass


class SimulationIsolationError(SimulationSafetyError):
    """Raised when simulation data isolation or sandbox boundaries are violated."""
    pass


# Production tool names that must NEVER be called from within simulation
BLOCKED_PRODUCTION_TOOLS = frozenset({
    "tool_executor",
    "execute_tool",
    "bash",
    "shell",
    "run_command",
    "file_writer",
    "write_to_file",
    "git_push",
    "deploy",
    "cloud_api",
    "database_mutate",
    "db_execute_write",
    "send_email",
    "send_message",
    "browser_action",
    "computer_control",
    "create_automation",
    "device_action",
})

# Patterns matching sensitive secrets to scrub
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret|password|bearer|auth[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
]

# Prompt injection patterns attempting to bypass simulation guards
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(previous|all)\s+instructions"),
    re.compile(r"(?i)bypass\s+(simulation|security|sandbox|policy)"),
    re.compile(r"(?i)execute\s+this\s+in\s+production"),
    re.compile(r"(?i)override\s+(execution_gate|approval|authorization)"),
    re.compile(r"(?i)mark\s+as\s+verified\s+without\s+checks"),
]


def assert_simulation_context(payload: dict[str, Any]) -> None:
    """Verifies that a payload is explicitly tagged as hypothetical simulation."""
    if payload.get("environment_label") != "SIMULATION_ONLY":
        raise SimulationIsolationError(
            f"Invalid environment label '{payload.get('environment_label')}'. Must be 'SIMULATION_ONLY'."
        )
    if payload.get("is_hypothetical") is not True:
        raise SimulationIsolationError("Payload must have is_hypothetical=True.")


def block_production_side_effects(action_name: str, target: str | None = None) -> None:
    """Hard firewall check: Blocks any attempt to invoke production side-effect tools or targets."""
    normalized_action = action_name.strip().lower()
    for blocked in BLOCKED_PRODUCTION_TOOLS:
        if blocked in normalized_action:
            raise SimulationSideEffectError(
                f"FIREWALL BLOCKED: Action '{action_name}' is a production side-effect tool and cannot be executed in simulation."
            )

    if target:
        normalized_target = target.strip().lower()
        if any(prod_indicator in normalized_target for prod_indicator in ("prod", "production", "live-db", "main-cluster", "prod-api")):
            raise ProductionMutationBlockedError(
                f"FIREWALL BLOCKED: Target '{target}' appears to be a production resource. Direct targeting from simulation is forbidden."
            )


def scrub_secrets(data: Any) -> Any:
    """Recursively redacts API keys, secrets, passwords, and tokens from dictionaries or strings."""
    if isinstance(data, str):
        cleaned = data
        # First pattern has group 1 for the key name
        cleaned = SECRET_PATTERNS[0].sub(r"\1: [REDACTED_SIMULATION_SECRET]", cleaned)
        for pattern in SECRET_PATTERNS[1:]:
            cleaned = pattern.sub("[REDACTED_SIMULATION_SECRET]", cleaned)
        return cleaned
    elif isinstance(data, dict):
        cleaned_dict = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ("secret", "password", "token", "api_key", "private_key", "credential")):
                cleaned_dict[k] = "[REDACTED_SIMULATION_SECRET]"
            else:
                cleaned_dict[k] = scrub_secrets(v)
        return cleaned_dict
    elif isinstance(data, list):
        return [scrub_secrets(item) for item in data]
    return data


def sanitize_scenario_input(content: str) -> str:
    """Detects and neutralizes prompt injection patterns in scenario input descriptions."""
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(content):
            # We disarm the pattern and append a security flag
            content = pattern.sub("[DISARMED_SIMULATION_DIRECTIVE]", content)
    return content


def tag_simulated_output(output: dict[str, Any]) -> dict[str, Any]:
    """Ensures that every simulation output contains required hypothetical markings."""
    output["environment_label"] = "SIMULATION_ONLY"
    output["is_hypothetical"] = True
    output["label"] = "SIMULATED"
    output["is_observed_fact"] = False
    return output
