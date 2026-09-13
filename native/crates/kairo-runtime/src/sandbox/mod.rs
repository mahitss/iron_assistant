pub mod capabilities;
pub mod computer;
pub mod executor;
pub mod policy;
pub mod process;
pub mod resources;
pub mod workspace;

pub use capabilities::{SandboxCapabilityContract, SandboxCapabilityRegistry};
pub use computer::{InputStateTracker, NativeComputerSubstrate};
pub use executor::SandboxExecutor;
pub use policy::{calculate_effective_policy, normalize_path, validate_path_safety};
pub use process::{
    build_sanitized_environment, configure_sandboxed_command, JobMetrics, ProcessJobContainer,
};
pub use resources::{
    build_resource_telemetry, evaluate_resource_violations, CROSS_PLATFORM_MATRIX,
};
pub use workspace::{clean_stale_workspaces, IsolatedWorkspace};
