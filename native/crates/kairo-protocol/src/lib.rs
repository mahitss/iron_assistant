pub mod budget;
pub mod capabilities;
pub mod computer;
pub mod contract;
pub mod envelope;
pub mod error;
pub mod health;
pub mod network;
pub mod sandbox;
pub mod telemetry;

pub use budget::{
    ResourceBudget, MAX_ALLOWED_CONCURRENCY, MAX_ALLOWED_DISK_BYTES, MAX_ALLOWED_DURATION_MS,
    MAX_ALLOWED_FILE_COUNT, MAX_ALLOWED_MEMORY_BYTES, MAX_ALLOWED_OUTPUT_BYTES,
};
pub use capabilities::{CapabilityDescriptor, ExecutionClass, SideEffectClass};
pub use computer::{
    ComputerOperationResult, DisplayMetadata, InputPrimitive, InputState, MouseButton,
    ProcessMetadata, TargetContext, VerificationStatus, WindowMetadata, WindowRect,
};
pub use contract::{
    AuthorizationContext, CapabilityStatus, ConnectionState, EnforcementLevel,
    MessageLifecycleState, OperationTargetContext, ProtocolErrorEnvelope, ProtocolMessageType,
    ProtocolVersion, ResourceAllocationContext, RuntimeState,
};
pub use envelope::{
    RequestContext, ResponseStatus, RuntimeRequest, RuntimeResponse, TimingMetadata,
    CURRENT_PROTOCOL_VERSION,
};
pub use error::{ErrorCategory, RuntimeError};
pub use health::{HealthState, RuntimeHealth, RuntimeMetadata};
pub use network::{
    DnsResolveRequest, DnsResolveResult, HttpRequestDescriptor, HttpResponseResult,
    NetworkHealthReport, NetworkOperationClass, NetworkPolicy as NetworkExecutionPolicy,
    NetworkProtocol,
};
pub use sandbox::{
    EnforcementAction, EnvironmentMode, EnvironmentPolicy, ExecutionRequest, ExecutionResult,
    ExecutionState, FilesystemMode, FilesystemPolicy, MeasurementQuality, NetworkMode,
    NetworkPolicy, OutputLimits, OutputMetadata, PlatformSupportSummary, PreflightResult,
    ProcessTreePolicy, ResourceUsageTelemetry, ResourceViolation, ResourceViolationType,
    SandboxPolicy, SandboxProfile, VerificationMetadata, ViolationSeverity,
};
pub use telemetry::{
    NativeEvent, NativeExecutionDomain, NativeOutcome, NativePrivacyClass, NativeSeverity,
    NativeSpanRecord,
};
