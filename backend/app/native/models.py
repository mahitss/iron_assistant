"""
Kairo Native Runtime Protocol Models (Pydantic v2).
Mirrors native/crates/kairo-protocol definitions for strong typing and serialization.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    # Task 87 Protocol Contract categories
    SESSION_INVALID = "SESSION_INVALID"
    REQUEST_EXPIRED = "REQUEST_EXPIRED"
    REQUEST_REPLAYED = "REQUEST_REPLAYED"
    REQUEST_DUPLICATE = "REQUEST_DUPLICATE"
    TARGET_CHANGED = "TARGET_CHANGED"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    PROTOCOL_BACKPRESSURE = "PROTOCOL_BACKPRESSURE"
    INCOMPATIBLE_VERSION = "INCOMPATIBLE_VERSION"


class ProtocolVersion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    major: int = 1
    minor: int = 0
    patch: int = 0

    @classmethod
    def from_string(cls, version_str: str) -> "ProtocolVersion":
        parts = version_str.strip().split(".")
        try:
            major = int(parts[0]) if len(parts) > 0 else 1
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return cls(major=major, minor=minor, patch=patch)
        except Exception:
            return cls(major=1, minor=0, patch=0)

    parse = from_string

    def is_compatible_with(self, other: "ProtocolVersion") -> bool:
        return self.major == other.major and self.minor >= other.minor

    def negotiate(self, other: "ProtocolVersion") -> Optional["ProtocolVersion"]:
        if self.major != other.major:
            return None
        min_minor = min(self.minor, other.minor)
        min_patch = min(self.patch, other.patch) if self.minor == other.minor else 0
        return ProtocolVersion(major=self.major, minor=min_minor, patch=min_patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class ProtocolMessageType(str, Enum):
    HANDSHAKE_HELLO = "HANDSHAKE_HELLO"
    HANDSHAKE_RESPONSE = "HANDSHAKE_RESPONSE"
    EXECUTION_REQUEST = "EXECUTION_REQUEST"
    EXECUTION_RESPONSE = "EXECUTION_RESPONSE"
    CANCEL_REQUEST = "CANCEL_REQUEST"
    CANCEL_RESPONSE = "CANCEL_RESPONSE"
    STOP_REQUEST = "STOP_REQUEST"
    STOP_RESPONSE = "STOP_RESPONSE"
    HEARTBEAT_PING = "HEARTBEAT_PING"
    HEARTBEAT_PONG = "HEARTBEAT_PONG"
    DRAIN_REQUEST = "DRAIN_REQUEST"
    DRAIN_RESPONSE = "DRAIN_RESPONSE"


class RuntimeState(str, Enum):
    STARTING = "STARTING"
    NEGOTIATING = "NEGOTIATING"
    AUTHENTICATING = "AUTHENTICATING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DRAINING = "DRAINING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNAUTHORIZED = "UNAUTHORIZED"

    def accepts_requests(self) -> bool:
        return self in (RuntimeState.READY, RuntimeState.DEGRADED)


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ESTABLISHED = "CONNECTED"
    AUTHENTICATING = "AUTHENTICATING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DRAINING = "DRAINING"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


class MessageLifecycleState(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    ACCEPTED = "ACCEPTED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    RESOURCE_EXCEEDED = "RESOURCE_EXCEEDED"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"

    def is_terminal(self) -> bool:
        return self in (
            MessageLifecycleState.COMPLETED,
            MessageLifecycleState.FAILED,
            MessageLifecycleState.REJECTED,
            MessageLifecycleState.CANCELLED,
            MessageLifecycleState.TIMED_OUT,
            MessageLifecycleState.RESOURCE_EXCEEDED,
            MessageLifecycleState.EMERGENCY_STOPPED,
            MessageLifecycleState.UNKNOWN_OUTCOME,
        )


class EnforcementLevel(str, Enum):
    HARDWARE_MMU_JOB_OBJECT = "HARDWARE_MMU_JOB_OBJECT"
    SOFTWARE_BOUNDED = "SOFTWARE_BOUNDED"
    INSPECTION_ONLY = "INSPECTION_ONLY"
    DEGRADED = "DEGRADED"
    UNSUPPORTED = "UNSUPPORTED"


class CapabilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    DEGRADED = "DEGRADED"
    UNSUPPORTED = "UNSUPPORTED"


class RuntimeErrorModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: ErrorCategory
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retryable: bool = False


class ProtocolErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    error_code: str
    category: ErrorCategory
    message: str
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    retryable: bool = False
    terminal: bool = True
    component: str = "native_runtime"
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    details: Optional[Dict[str, Any]] = None


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


class AuthorizationContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    policy_id: Optional[str] = None
    security_level: str = "standard"
    approval_id: Optional[str] = None
    approved_tool: Optional[str] = None
    approved_target: Optional[str] = None
    granted_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    expires_at: Optional[datetime.datetime] = None
    signature_hash: Optional[str] = None

    def is_expired(self, now: Optional[datetime.datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        n = now or datetime.datetime.now(datetime.timezone.utc)
        return n > self.expires_at

    def validates_binding(self, requested_tool: str, requested_target: Optional[str] = None) -> bool:
        if self.approved_tool is not None and self.approved_tool != requested_tool:
            return False
        if self.approved_target is not None and requested_target is not None and self.approved_target != requested_target:
            return False
        return True


class ResourceAllocationContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    allocation_id: str
    request_id: str
    capability_id: str
    limits: ResourceBudget = Field(default_factory=ResourceBudget)
    remaining_budget: Optional[ResourceBudget] = None
    expires_at: datetime.datetime

    def is_expired(self, now: Optional[datetime.datetime] = None) -> bool:
        n = now or datetime.datetime.now(datetime.timezone.utc)
        return n > self.expires_at

    def matches_request(self, request_id: str, capability_id: str) -> bool:
        return self.request_id == request_id and self.capability_id == capability_id


class OperationTargetContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_type: str
    target_identifier: str
    expected_hash: Optional[str] = None


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
    enforcement_level: EnforcementLevel = EnforcementLevel.HARDWARE_MMU_JOB_OBJECT
    platform: str = "windows"
    resource_features: List[str] = Field(default_factory=list)
    security_features: List[str] = Field(default_factory=list)
    supported_protocol_versions: List[str] = Field(default_factory=lambda: ["1.0", "1.0.0"])
    status: CapabilityStatus = CapabilityStatus.SUPPORTED


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
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


class TimingMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    queue_time_ms: int = 0
    execution_time_ms: int = 0
    total_time_ms: int = 0


# =============================================================================
# Telemetry & Observability Fabric Models (Task 86)
# =============================================================================

class NativeSeverity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class NativePrivacyClass(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


class NativeExecutionDomain(str, Enum):
    NATIVE_RUNTIME = "NATIVE_RUNTIME"
    SANDBOX = "SANDBOX"
    COMPUTER_INTERACTION = "COMPUTER_INTERACTION"
    NETWORK_FABRIC = "NETWORK_FABRIC"
    TOOL_FABRIC = "TOOL_FABRIC"
    HARDWARE_ISOLATION = "HARDWARE_ISOLATION"


class NativeOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    BLOCK = "BLOCK"
    DENY = "DENY"
    CANCEL = "CANCEL"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


class NativeEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_id: str
    event_type: str
    monotonic_timestamp_ns: int = 0
    wall_timestamp_utc: Optional[Any] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    execution_domain: Optional[str] = "RUNTIME"
    domain: Optional[str] = None
    severity: Optional[str] = "INFO"
    privacy_class: Optional[str] = "INTERNAL"
    outcome: Optional[str] = "SUCCESS"
    component: Optional[str] = "rust_runtime"
    source: Optional[str] = None
    timestamp_nanos: Optional[int] = None
    monotonic_nanos: Optional[int] = None
    duration_nanos: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def populate_aliases(self) -> "NativeEvent":
        if self.monotonic_nanos is None and self.monotonic_timestamp_ns:
            self.monotonic_nanos = self.monotonic_timestamp_ns
        elif not self.monotonic_timestamp_ns and self.monotonic_nanos:
            self.monotonic_timestamp_ns = self.monotonic_nanos
        if self.timestamp_nanos is None and self.monotonic_timestamp_ns:
            self.timestamp_nanos = self.monotonic_timestamp_ns
        return self

    @property
    def effective_domain(self) -> str:
        return self.execution_domain or self.domain or "RUNTIME"

    @property
    def effective_source(self) -> str:
        return self.component or self.source or "rust_runtime"

    @property
    def effective_monotonic_nanos(self) -> int:
        return self.monotonic_timestamp_ns or self.monotonic_nanos or 0



class RuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_type: ProtocolMessageType = ProtocolMessageType.EXECUTION_REQUEST
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol_version: str = CURRENT_PROTOCOL_VERSION
    operation: str
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    deadline_ms: Optional[int] = 30000
    cancellation_id: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    causation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    runtime_instance_id: Optional[str] = None
    client_instance_id: Optional[str] = None
    session_id: Optional[str] = None
    capability_id: Optional[str] = None
    capability_version: Optional[str] = "1.0"
    created_at: Optional[datetime.datetime] = None
    deadline: Optional[datetime.datetime] = None
    authorization_context: Optional[AuthorizationContext] = None
    resource_context: Optional[ResourceAllocationContext] = None
    target_context: Optional[OperationTargetContext] = None
    nonce: Optional[str] = None
    idempotency_key: Optional[str] = None
    caller_context: Optional[RequestContext] = None
    capability: Optional[str] = None
    resource_budget: Optional[ResourceBudget] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class RuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_type: Optional[ProtocolMessageType] = None
    message_id: Optional[str] = None
    request_id: str
    protocol_version: str
    status: ResponseStatus
    execution_state: Optional[MessageLifecycleState] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[RuntimeErrorModel] = None
    error_envelope: Optional[ProtocolErrorEnvelope] = None
    runtime_metadata: Optional[RuntimeMetadata] = None
    runtime_instance_id: Optional[str] = None
    session_id: Optional[str] = None
    timing: Optional[TimingMetadata] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    causation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    native_events: Optional[List[NativeEvent]] = None



class HandshakeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol_version: str = CURRENT_PROTOCOL_VERSION
    secret: Optional[str] = None
    client_id: str = "kairo-python-backend"
    client_version: str = "1.0.0"
    client_instance_id: Optional[str] = None
    nonce: Optional[str] = None
    requested_capabilities: Optional[List[str]] = None


class HandshakeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol_version: str
    runtime_version: str
    authenticated: bool
    runtime_instance_id: Optional[str] = None
    session_id: Optional[str] = None
    capability_fingerprint: Optional[str] = None
    configuration_fingerprint: Optional[str] = None
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



# =============================================================================
# Native Computer Interaction Substrate Models (Task 84)
# =============================================================================

class ProcessMetadata(BaseModel):
    """Controlled process metadata snapshot from native substrate."""
    model_config = ConfigDict(extra="ignore")

    pid: int
    name: str
    ppid: Optional[int] = None
    create_time: Optional[int] = None
    is_alive: bool = True
    memory_bytes: Optional[int] = None
    cpu_percent: Optional[float] = None


class WindowRect(BaseModel):
    """Geometry of a window on screen."""
    model_config = ConfigDict(extra="ignore")

    x: int
    y: int
    width: int
    height: int


class WindowMetadata(BaseModel):
    """Controlled window metadata snapshot from native substrate."""
    model_config = ConfigDict(extra="ignore")

    window_id: int
    title: str
    pid: int
    process_name: str
    rect: WindowRect
    is_visible: bool = True
    is_focused: bool = False


class DisplayMetadata(BaseModel):
    """Display monitor metadata and coordinate space bounds."""
    model_config = ConfigDict(extra="ignore")

    display_id: int
    name: str
    width: int
    height: int
    scale_factor: float = 1.0
    is_primary: bool = True


class TargetContext(BaseModel):
    """
    Context binding an input action to an expected target window/process.
    Prevents ambiguous coordinate-only actions and race condition misfires.
    """
    model_config = ConfigDict(extra="ignore")

    window_id: Optional[int] = None
    expected_title: Optional[str] = None
    expected_pid: Optional[int] = None
    expected_process_name: Optional[str] = None
    coordinate: Optional[tuple[int, int]] = None
    display_id: Optional[int] = None


class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class VerificationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    UNVERIFIED = "UNVERIFIED"
    FAILED = "FAILED"


class InputState(BaseModel):
    """Active input state snapshot tracked by native substrate."""
    model_config = ConfigDict(extra="ignore")

    pressed_keys: List[str] = Field(default_factory=list)
    pressed_buttons: List[str] = Field(default_factory=list)
    active_operation: Optional[str] = None


class ComputerOperationResult(BaseModel):
    """Structured result returned by native computer control operations."""
    model_config = ConfigDict(extra="ignore")

    success: bool
    action: str
    target_verified: bool
    verification_status: VerificationStatus
    duration_ms: int
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Task 85 — Native Network Execution & Connection Fabric Models
# ============================================================================

class NetworkOperationClass(str, Enum):
    OBSERVE = "OBSERVE"
    FETCH = "FETCH"
    STREAM = "STREAM"
    CONNECT = "CONNECT"
    RESOLVE = "RESOLVE"
    UPLOAD = "UPLOAD"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    EXTERNAL_DESTRUCTIVE = "EXTERNAL_DESTRUCTIVE"


class NetworkProtocol(str, Enum):
    HTTP1 = "HTTP1"
    HTTP2 = "HTTP2"
    TCP = "TCP"
    DNS = "DNS"
    TLS = "TLS"
    WEBSOCKET = "WEBSOCKET"


class NetworkExecutionPolicy(BaseModel):
    """Governed policy constraints applied to native network operations."""
    model_config = ConfigDict(extra="ignore")

    hostname_policy: List[str] = Field(default_factory=list)
    denied_hostnames: List[str] = Field(default_factory=list)
    port_policy: List[int] = Field(default_factory=lambda: [80, 443])
    allow_private_ips: bool = False
    dns_timeout_ms: int = 5000
    connect_timeout_ms: int = 5000
    request_timeout_ms: int = 15000
    total_deadline_ms: int = 30000
    max_redirects: int = 5
    allow_cross_origin_redirects: bool = True
    strip_credentials_cross_origin: bool = True
    request_size_limit_bytes: int = 1048576  # 1MB
    response_size_limit_bytes: int = 10485760  # 10MB
    max_retries: int = 2
    rate_limit_rpm: int = 120


class DnsResolveRequest(BaseModel):
    """Request payload for bounded DNS resolution."""
    model_config = ConfigDict(extra="ignore")

    hostname: str
    policy: Optional[NetworkExecutionPolicy] = None


class DnsResolveResult(BaseModel):
    """Result payload from native bounded DNS resolution."""
    model_config = ConfigDict(extra="ignore")

    hostname: str
    resolved_ips: List[str] = Field(default_factory=list)
    is_public: bool = True
    ttl_seconds: int = 60
    duration_ms: int = 0
    error: Optional[str] = None


class HttpRequestDescriptor(BaseModel):
    """Strongly-typed native HTTP request descriptor."""
    model_config = ConfigDict(extra="ignore")

    method: str = "GET"
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    operation_class: NetworkOperationClass = NetworkOperationClass.FETCH
    idempotency_key: Optional[str] = None
    policy: Optional[NetworkExecutionPolicy] = None


class HttpResponseResult(BaseModel):
    """Strongly-typed native HTTP response result."""
    model_config = ConfigDict(extra="ignore")

    status_code: int
    status_text: str = "OK"
    headers: Dict[str, str] = Field(default_factory=dict)
    body: str = ""
    truncated: bool = False
    raw_bytes_count: int = 0
    duration_ms: int = 0
    dns_latency_ms: int = 0
    connect_latency_ms: int = 0
    redirect_chain: List[str] = Field(default_factory=list)
    remote_address: Optional[str] = None
    protocol: str = "HTTP/1.1"
    security_classification: str = "UNTRUSTED_REMOTE_CONTENT"
    error: Optional[str] = None


class NetworkHealthReport(BaseModel):
    """Operational health and telemetry report for the native network substrate."""
    model_config = ConfigDict(extra="ignore")

    state: str = "HEALTHY"
    active_connections: int = 0
    idle_connections: int = 0
    active_requests: int = 0
    total_requests: int = 0
    ssrf_blocks_count: int = 0
    circuit_breaker_open: bool = False
    pool_utilization: float = 0.0




