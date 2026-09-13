"""
Kairo Native Runtime Protocol Models (Pydantic v2).
Mirrors native/crates/kairo-protocol definitions for strong typing and serialization.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

CURRENT_PROTOCOL_VERSION = "1.0"


class ErrorCategory(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    CANCELLED = "CANCELLED"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class RuntimeErrorModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: ErrorCategory
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retryable: bool = False


class ExecutionClass(str, Enum):
    PURE_COMPUTE = "PURE_COMPUTE"
    IO_BOUNDED = "IO_BOUNDED"
    SYSTEM_INSPECTION = "SYSTEM_INSPECTION"
    PRIVILEGED_NATIVE = "PRIVILEGED_NATIVE"


class SideEffectClass(str, Enum):
    NONE = "NONE"
    READ_ONLY = "READ_ONLY"
    STATEFUL_LOCAL = "STATEFUL_LOCAL"
    EXTERNAL_MUTATION = "EXTERNAL_MUTATION"


class ResourceBudget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_cpu_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    max_memory_bytes: Optional[int] = Field(default=None, gt=0)
    max_execution_time_ms: Optional[int] = Field(default=None, gt=0, le=300000)
    max_concurrency: Optional[int] = Field(default=None, gt=0, le=64)
    max_output_bytes: Optional[int] = Field(default=None, gt=0)
    max_disk_bytes: Optional[int] = Field(default=None, gt=0)
    max_file_count: Optional[int] = Field(default=None, gt=0)


class CapabilityDescriptor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    capability_id: str
    name: str
    version: str
    description: str
    available: bool = True
    execution_class: ExecutionClass
    side_effect_class: SideEffectClass
    supported_operations: List[str]
    default_budget: Optional[ResourceBudget] = None


class HealthState(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DRAINING = "DRAINING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class RuntimeMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    runtime_version: str
    protocol_version: str = CURRENT_PROTOCOL_VERSION
    build_id: str
    platform: str
    arch: str
    uptime_seconds: int
    active_requests: int
    capabilities: List[str] = Field(default_factory=list)


class RuntimeHealth(BaseModel):
    model_config = ConfigDict(extra="ignore")

    state: HealthState
    healthy: bool
    message: str
    metadata: RuntimeMetadata
    last_heartbeat: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    security_level: Optional[str] = None
    auth_token_hash: Optional[str] = None
    client_version: Optional[str] = "1.0.0"


class ResponseStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class TimingMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    queue_time_ms: int = 0
    execution_time_ms: int = 0
    total_time_ms: int = 0


class RuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol_version: str = CURRENT_PROTOCOL_VERSION
    operation: str
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    deadline_ms: Optional[int] = 30000
    cancellation_id: Optional[str] = None
    correlation_id: Optional[str] = None
    caller_context: Optional[RequestContext] = None
    capability: Optional[str] = None
    resource_budget: Optional[ResourceBudget] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class RuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str
    protocol_version: str
    status: ResponseStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[RuntimeErrorModel] = None
    runtime_metadata: Optional[RuntimeMetadata] = None
    timing: Optional[TimingMetadata] = None
    correlation_id: Optional[str] = None


class HandshakeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol_version: str = CURRENT_PROTOCOL_VERSION
    secret: Optional[str] = None
    client_id: str = "kairo-python-backend"
    client_version: str = "1.0.0"


class HandshakeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol_version: str
    runtime_version: str
    authenticated: bool
    error: Optional[str] = None
    capabilities: List[CapabilityDescriptor] = Field(default_factory=list)


# =============================================================================
# Sandbox Models (Task 81)
# =============================================================================

class SandboxProfile(str, Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    STRICT = "STRICT"


class FilesystemMode(str, Enum):
    NO_ACCESS = "NO_ACCESS"
    READ_ONLY = "READ_ONLY"
    READ_WRITE = "READ_WRITE"


class FilesystemPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: FilesystemMode = FilesystemMode.READ_ONLY
    allowed_read_roots: List[str] = Field(default_factory=list)
    allowed_write_roots: List[str] = Field(default_factory=list)
    isolated_workspace: bool = True


class NetworkMode(str, Enum):
    NO_NETWORK = "NO_NETWORK"
    LOOPBACK_ONLY = "LOOPBACK_ONLY"
    ALLOWLIST = "ALLOWLIST"
    CONTROLLED = "CONTROLLED"


class NetworkPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: NetworkMode = NetworkMode.NO_NETWORK
    allowed_hosts: List[str] = Field(default_factory=list)


class EnvironmentMode(str, Enum):
    EMPTY = "EMPTY"
    ALLOWLIST = "ALLOWLIST"
    INHERIT_SAFE = "INHERIT_SAFE"
    EXPLICIT = "EXPLICIT"


class EnvironmentPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: EnvironmentMode = EnvironmentMode.ALLOWLIST
    allowed_variables: List[str] = Field(
        default_factory=lambda: [
            "PATH",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "HOME",
            "TMPDIR",
        ]
    )
    explicit_variables: Dict[str, str] = Field(default_factory=dict)


class ProcessTreePolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    allow_child_processes: bool = False
    max_children: int = 0
    kill_on_parent_exit: bool = True


class OutputLimits(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_stdout_bytes: int = 1024 * 1024       # 1 MiB
    max_stderr_bytes: int = 1024 * 1024       # 1 MiB
    max_combined_bytes: int = 2 * 1024 * 1024 # 2 MiB


class SandboxPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profile: SandboxProfile = SandboxProfile.STANDARD
    filesystem: FilesystemPolicy = Field(default_factory=FilesystemPolicy)
    network: NetworkPolicy = Field(default_factory=NetworkPolicy)
    environment: EnvironmentPolicy = Field(default_factory=EnvironmentPolicy)
    process_tree: ProcessTreePolicy = Field(default_factory=ProcessTreePolicy)
    output_limits: OutputLimits = Field(default_factory=OutputLimits)
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)


class ExecutionState(str, Enum):
    QUEUED = "QUEUED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    KILLED = "KILLED"
    REJECTED = "REJECTED"
    RESOURCE_EXCEEDED = "RESOURCE_EXCEEDED"


class ExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    capability_id: str
    arguments: List[str] = Field(default_factory=list)
    working_directory: Optional[str] = None
    environment_policy: EnvironmentPolicy = Field(default_factory=EnvironmentPolicy)
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    output_limits: OutputLimits = Field(default_factory=OutputLimits)
    authorization_context: Optional[RequestContext] = None
    sandbox_policy: SandboxPolicy = Field(default_factory=SandboxPolicy)
    correlation_id: Optional[str] = None
    cancellation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class OutputMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stdout_bytes: int = 0
    stderr_bytes: int = 0
    truncated: bool = False
    output_limit_exceeded: bool = False


class VerificationMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    process_exited: bool = True
    descendants_cleaned: bool = True
    workspace_cleaned: bool = True
    resources_released: bool = True


class MeasurementQuality(str, Enum):
    EXACT = "EXACT"
    ESTIMATED = "ESTIMATED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class ResourceUsageTelemetry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wall_time_ms: int = 0
    cpu_time_ms: Optional[int] = None
    peak_memory_bytes: Optional[int] = None
    current_memory_bytes: Optional[int] = None
    process_count: int = 0
    output_bytes: int = 0
    workspace_bytes: int = 0
    file_count: int = 0
    measurement_quality: MeasurementQuality = MeasurementQuality.PARTIAL


class ResourceViolationType(str, Enum):
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    CPU_LIMIT_EXCEEDED = "CPU_LIMIT_EXCEEDED"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    PROCESS_LIMIT_EXCEEDED = "PROCESS_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    DISK_LIMIT_EXCEEDED = "DISK_LIMIT_EXCEEDED"
    FILE_COUNT_LIMIT_EXCEEDED = "FILE_COUNT_LIMIT_EXCEEDED"


class ViolationSeverity(str, Enum):
    WARNING = "WARNING"
    SOFT_LIMIT = "SOFT_LIMIT"
    HARD_LIMIT = "HARD_LIMIT"
    CRITICAL = "CRITICAL"


class EnforcementAction(str, Enum):
    OBSERVE = "OBSERVE"
    WARN = "WARN"
    THROTTLE = "THROTTLE"
    TERMINATE = "TERMINATE"


class ResourceViolation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    violation_type: ResourceViolationType
    severity: ViolationSeverity = ViolationSeverity.HARD_LIMIT
    limit_value: int = 0
    actual_value: int = 0
    unit: str = ""
    message: str = ""
    enforcement_action: EnforcementAction = EnforcementAction.TERMINATE


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str
    execution_id: str
    capability_id: str
    state: ExecutionState
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    output_metadata: OutputMetadata = Field(default_factory=OutputMetadata)
    duration_ms: int = 0
    resource_usage: Optional[ResourceBudget] = None
    resource_telemetry: Optional[ResourceUsageTelemetry] = None
    resource_violation: Optional[ResourceViolation] = None
    cancellation_state: Optional[str] = None
    timeout_state: bool = False
    failure_classification: Optional[str] = None
    verification_metadata: VerificationMetadata = Field(default_factory=VerificationMetadata)
    error: Optional[RuntimeErrorModel] = None
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class PlatformSupportSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    os: str
    arch: str
    job_objects_supported: bool
    process_groups_supported: bool
    isolated_temp_workspace: bool
    stream_bounding_supported: bool
    network_isolation_status: str


class PreflightResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accepted: bool
    capability_id: str
    effective_policy: SandboxPolicy
    effective_budget: ResourceBudget
    rejection_reason: Optional[str] = None
    platform_support: Optional[PlatformSupportSummary] = None


# =============================================================================
# Native Tool Execution Fabric Models (Task 83)
# =============================================================================

class ToolExecutionClass(str, Enum):
    PYTHON = "PYTHON"
    NATIVE_RUST = "NATIVE_RUST"
    REMOTE = "REMOTE"
    COMPOSITE = "COMPOSITE"


class ToolExecutionPreference(str, Enum):
    NATIVE_REQUIRED = "NATIVE_REQUIRED"
    NATIVE_PREFERRED = "NATIVE_PREFERRED"
    PYTHON_PREFERRED = "PYTHON_PREFERRED"
    PYTHON_REQUIRED = "PYTHON_REQUIRED"


class ToolAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"
    INCOMPATIBLE = "INCOMPATIBLE"


class ToolInvocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    invocation_id: str
    tool_name: str
    tool_version: str = "1.0.0"
    capability_id: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    session_id: Optional[str] = None
    approval_id: Optional[str] = None
    deadline_ms: Optional[int] = 30000
    cancellation_id: Optional[str] = None
    correlation_id: Optional[str] = None


# Alias for execution authorization context
AuthorizationContext = RequestContext


