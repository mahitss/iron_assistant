"""Native Rust-backed tools executing within Kairo's secure isolated sandbox substrate."""

import hashlib
import platform
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.tools.base import (
    BaseTool,
    ToolExecutionClass,
    ToolExecutionPreference,
)
from app.tools.permissions import PermissionLevel


# =============================================================================
# 1. Native Hash Tool
# =============================================================================

class NativeHashArgs(BaseModel):
    """Input arguments for native cryptographic hash calculation."""

    text: str = Field(..., min_length=0, max_length=1_000_000, description="Input string to hash")
    algorithm: str = Field(default="sha256", description="Hash algorithm to use (default: sha256)")


class NativeHashOutput(BaseModel):
    """Structured output for native hash calculation."""

    sha256: str = Field(..., min_length=64, max_length=64, description="Calculated 64-character hex digest")
    bytes: int = Field(..., ge=0, description="Length of hashed byte input")


class NativeHashTool(BaseTool):
    """Calculates cryptographic hashes using the high-performance native Rust substrate."""

    name = "native_hash"
    description = (
        "Compute deterministic cryptographic SHA-256 hash using the native Rust sandbox substrate. "
        "High performance, constant memory footprint, and sandboxed execution."
    )
    version = "1.0.0"
    permission_level = PermissionLevel.READ
    execution_class = ToolExecutionClass.NATIVE_RUST
    preference = ToolExecutionPreference.NATIVE_PREFERRED
    capability_id = "sandbox.hash"
    sandbox_profile = "STANDARD"
    args_model = NativeHashArgs
    output_model = NativeHashOutput
    timeout_seconds = 10.0
    idempotent = True

    async def execute(self, text: str, algorithm: str = "sha256", **kwargs: Any) -> dict[str, Any]:
        """Safe Python fallback implementation used if native runtime is offline."""
        data = text.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        return {"sha256": digest, "bytes": len(data)}

    def verify(self, result: Any) -> bool:
        """Verify that the result contains a valid 64-character hex hash."""
        if not isinstance(result, dict):
            return False
        digest = result.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            return False
        try:
            int(digest, 16)
            return True
        except ValueError:
            return False


# =============================================================================
# 2. Native System Info Tool
# =============================================================================

class NativeSystemInfoArgs(BaseModel):
    """No input arguments required for system information query."""


class NativeSystemInfoOutput(BaseModel):
    """Structured output for host platform and runtime substrate information."""

    os: str = Field(..., description="Operating system platform name")
    architecture: str = Field(..., description="Hardware CPU architecture")
    cores: int = Field(..., ge=1, description="Available CPU compute cores")
    runtime_version: str = Field(..., description="Native runtime substrate build version")
    is_sandboxed: bool = Field(..., description="True if executed within sandbox boundary")


class NativeSystemInfoTool(BaseTool):
    """Retrieves safe host platform and hardware details directly from native substrate."""

    name = "native_system_info"
    description = (
        "Retrieve safe, read-only host platform and hardware metrics directly from the "
        "native Rust runtime substrate (OS, architecture, cores, runtime version)."
    )
    version = "1.0.0"
    permission_level = PermissionLevel.READ
    execution_class = ToolExecutionClass.NATIVE_RUST
    preference = ToolExecutionPreference.NATIVE_PREFERRED
    capability_id = "native.sysinfo"
    sandbox_profile = "MINIMAL"
    args_model = NativeSystemInfoArgs
    output_model = NativeSystemInfoOutput
    timeout_seconds = 10.0
    idempotent = True

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Safe Python fallback implementation."""
        import os
        return {
            "os": platform.system(),
            "architecture": platform.machine(),
            "cores": os.cpu_count() or 1,
            "runtime_version": "0.1.0-python-fallback",
            "is_sandboxed": False,
        }

    def verify(self, result: Any) -> bool:
        """Verify result contains required platform metadata."""
        if not isinstance(result, dict):
            return False
        required = {"os", "architecture", "cores", "runtime_version", "is_sandboxed"}
        return required.issubset(result.keys())


# =============================================================================
# 3. Native Workspace Inspector Tool
# =============================================================================

class NativeWorkspaceInspectArgs(BaseModel):
    """Input arguments for inspecting workspace files safely."""

    path: str = Field(..., min_length=1, max_length=256, description="Relative path within workspace to inspect")
    content: Optional[str] = Field(default=None, description="Optional text content to initialize in workspace for inspection")


class NativeWorkspaceInspectOutput(BaseModel):
    """Structured output for workspace file inspection."""

    path: str = Field(..., description="Relative file path inspected")
    size_bytes: int = Field(..., ge=0, description="Exact file size in bytes")
    is_file: bool = Field(..., description="True if target is a regular file")
    is_dir: bool = Field(..., description="True if target is a directory")
    is_binary: bool = Field(..., description="True if binary content was detected")
    line_count: int = Field(..., ge=0, description="Total text line count")
    sha256: str = Field(..., min_length=64, max_length=64, description="Cryptographic SHA-256 checksum")


class NativeWorkspaceInspectTool(BaseTool):
    """Inspects files within the sandboxed workspace boundary with cryptographic verification."""

    name = "native_workspace_inspect"
    description = (
        "Inspect workspace files within the isolated native sandbox. Calculates exact byte size, "
        "line counts, binary classification, and SHA-256 checksum. Strict path traversal rejection."
    )
    version = "1.0.0"
    permission_level = PermissionLevel.READ
    execution_class = ToolExecutionClass.NATIVE_RUST
    preference = ToolExecutionPreference.NATIVE_REQUIRED  # STRICT FAIL-CLOSED REQUIREMENT
    capability_id = "native.file.inspect"
    sandbox_profile = "STANDARD"
    args_model = NativeWorkspaceInspectArgs
    output_model = NativeWorkspaceInspectOutput
    timeout_seconds = 15.0
    idempotent = True

    async def execute(self, path: str, content: Optional[str] = None, **kwargs: Any) -> dict[str, Any]:
        """NATIVE_REQUIRED tool: cannot execute without native sandbox substrate."""
        raise RuntimeError("NativeWorkspaceInspectTool requires native sandbox runtime substrate.")

    def verify(self, result: Any) -> bool:
        """Verify inspection output integrity."""
        if not isinstance(result, dict):
            return False
        required = {"path", "size_bytes", "is_file", "is_binary", "line_count", "sha256"}
        return required.issubset(result.keys()) and len(result.get("sha256", "")) == 64


# =============================================================================
# 4. Native Security Probe Tool
# =============================================================================

class NativeProbeArgs(BaseModel):
    """Input arguments for native security and boundary probe."""

    mode: str = Field(default="normal", description="Probe mode: normal, sleep, flood, memory_burn, disk_flood, cpu_burn")
    megabytes: int = Field(default=10, ge=1, le=1024, description="Megabytes to allocate for memory_burn probe")
    duration_ms: int = Field(default=100, ge=0, le=30000, description="Duration in ms for sleep probe")
    files: int = Field(default=1, ge=1, le=50, description="Number of files for disk_flood probe")


class NativeProbeTool(BaseTool):
    """Controlled diagnostic probe to test timeouts, memory limits, and cancellation in sandbox."""

    name = "native_probe"
    description = (
        "Governed diagnostic probe to test low-level sandbox isolation, resource limits, "
        "and cooperative cancellation. Requires human approval context (EXECUTE permission level)."
    )
    version = "1.0.0"
    permission_level = PermissionLevel.EXECUTE  # REQUIRES APPROVAL
    execution_class = ToolExecutionClass.NATIVE_RUST
    preference = ToolExecutionPreference.NATIVE_REQUIRED
    capability_id = "sandbox.probe"
    sandbox_profile = "STANDARD"
    args_model = NativeProbeArgs
    timeout_seconds = 15.0
    idempotent = False

    async def execute(self, mode: str = "normal", **kwargs: Any) -> str:
        """NATIVE_REQUIRED: cannot execute without native substrate."""
        raise RuntimeError("NativeProbeTool requires native sandbox runtime substrate.")

    def verify(self, result: Any) -> bool:
        """Verify probe result string or dict."""
        return result is not None
