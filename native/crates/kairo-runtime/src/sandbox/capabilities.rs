use kairo_protocol::sandbox::{
    EnvironmentMode, EnvironmentPolicy, FilesystemMode, FilesystemPolicy, NetworkMode,
    NetworkPolicy, OutputLimits, ProcessTreePolicy, SandboxPolicy, SandboxProfile,
};
use kairo_protocol::{CapabilityDescriptor, ExecutionClass, ResourceBudget, SideEffectClass};
use std::collections::HashMap;

/// Sandbox capability registry defining typed contracts for sandboxed workloads.
#[derive(Clone)]
pub struct SandboxCapabilityRegistry {
    contracts: HashMap<String, SandboxCapabilityContract>,
}

/// Structured definition of a sandboxed capability contract.
#[derive(Debug, Clone)]
pub struct SandboxCapabilityContract {
    pub descriptor: CapabilityDescriptor,
    pub default_policy: SandboxPolicy,
    pub max_allowed_budget: ResourceBudget,
}

impl Default for SandboxCapabilityRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl SandboxCapabilityRegistry {
    pub fn new() -> Self {
        let mut reg = Self {
            contracts: HashMap::new(),
        };
        reg.register_builtins();
        reg
    }

    fn register_builtins(&mut self) {
        // 1. sandbox.preflight
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "sandbox.preflight",
                "Sandbox Preflight & Dry Run",
                "1.0.0",
                "Dry-run simulation calculating effective sandbox policy and validating constraints",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::None,
                vec!["sandbox.preflight".to_string()],
            ),
            default_policy: SandboxPolicy {
                profile: SandboxProfile::Standard,
                filesystem: FilesystemPolicy {
                    mode: FilesystemMode::NoAccess,
                    allowed_read_roots: vec![],
                    allowed_write_roots: vec![],
                    isolated_workspace: false,
                },
                network: NetworkPolicy {
                    mode: NetworkMode::NoNetwork,
                    allowed_hosts: vec![],
                },
                environment: EnvironmentPolicy {
                    mode: EnvironmentMode::Empty,
                    allowed_variables: vec![],
                    explicit_variables: HashMap::new(),
                },
                process_tree: ProcessTreePolicy::default(),
                output_limits: OutputLimits::default(),
                resource_budget: ResourceBudget::default(),
            },
            max_allowed_budget: ResourceBudget::default(),
        });

        // 2. sandbox.echo
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "sandbox.echo",
                "Sandbox Safe Echo",
                "1.0.0",
                "Deterministic echo capability for testing argument isolation and output capture",
                true,
                ExecutionClass::PureCompute,
                SideEffectClass::None,
                vec!["sandbox.echo".to_string()],
            ),
            default_policy: SandboxPolicy {
                profile: SandboxProfile::Standard,
                filesystem: FilesystemPolicy::default(),
                network: NetworkPolicy::default(),
                environment: EnvironmentPolicy::default(),
                process_tree: ProcessTreePolicy {
                    allow_child_processes: false,
                    max_children: 0,
                    kill_on_parent_exit: true,
                },
                output_limits: OutputLimits::default(),
                resource_budget: ResourceBudget::default(),
            },
            max_allowed_budget: ResourceBudget::default(),
        });

        // 3. sandbox.hash
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "sandbox.hash",
                "Sandbox Cryptographic Hash",
                "1.0.0",
                "Pure-compute cryptographic SHA-256 computation on payload or workspace file",
                true,
                ExecutionClass::PureCompute,
                SideEffectClass::None,
                vec!["sandbox.hash".to_string()],
            ),
            default_policy: SandboxPolicy {
                profile: SandboxProfile::Standard,
                filesystem: FilesystemPolicy {
                    mode: FilesystemMode::ReadWrite,
                    allowed_read_roots: vec![],
                    allowed_write_roots: vec![],
                    isolated_workspace: true,
                },
                network: NetworkPolicy::default(),
                environment: EnvironmentPolicy::default(),
                process_tree: ProcessTreePolicy::default(),
                output_limits: OutputLimits::default(),
                resource_budget: ResourceBudget::default(),
            },
            max_allowed_budget: ResourceBudget::default(),
        });

        // 4. sandbox.probe
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "sandbox.probe",
                "Sandbox Security & Adversarial Test Probe",
                "1.0.0",
                "Deterministic probe to test timeouts, cooperative cancellation, output flood, and child containment",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::None,
                vec!["sandbox.probe".to_string()],
            ),
            default_policy: SandboxPolicy {
                profile: SandboxProfile::Standard,
                filesystem: FilesystemPolicy {
                    mode: FilesystemMode::ReadWrite,
                    allowed_read_roots: vec![],
                    allowed_write_roots: vec![],
                    isolated_workspace: true,
                },
                network: NetworkPolicy::default(),
                environment: EnvironmentPolicy::default(),
                process_tree: ProcessTreePolicy {
                    allow_child_processes: true,
                    max_children: 4,
                    kill_on_parent_exit: true,
                },
                output_limits: OutputLimits::default(),
                resource_budget: ResourceBudget::default(),
            },
            max_allowed_budget: ResourceBudget {
                max_cpu_percent: Some(100.0),
                max_memory_bytes: Some(1024 * 1024 * 1024),
                max_execution_time_ms: Some(60_000),
                max_concurrency: Some(8),
                max_output_bytes: Some(10 * 1024 * 1024),
                max_disk_bytes: Some(512 * 1024 * 1024),
                max_file_count: Some(1000),
            },
        });

        // 5. sandbox.execute
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "sandbox.execute",
                "Sandbox Governed Execution",
                "1.0.0",
                "Secure governed execution for authorized capability workloads within isolated boundaries",
                true,
                ExecutionClass::PrivilegedNative,
                SideEffectClass::StatefulLocal,
                vec!["sandbox.execute".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 6. native.sysinfo
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.sysinfo",
                "Native System Information",
                "1.0.0",
                "Safe read-only host platform and hardware metrics collected directly by native runtime",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::None,
                vec!["native.sysinfo".to_string()],
            ),
            default_policy: SandboxPolicy {
                profile: SandboxProfile::Minimal,
                filesystem: FilesystemPolicy {
                    mode: FilesystemMode::NoAccess,
                    allowed_read_roots: vec![],
                    allowed_write_roots: vec![],
                    isolated_workspace: false,
                },
                network: NetworkPolicy {
                    mode: NetworkMode::NoNetwork,
                    allowed_hosts: vec![],
                },
                environment: EnvironmentPolicy {
                    mode: EnvironmentMode::Empty,
                    allowed_variables: vec![],
                    explicit_variables: HashMap::new(),
                },
                process_tree: ProcessTreePolicy::default(),
                output_limits: OutputLimits::default(),
                resource_budget: ResourceBudget::default(),
            },
            max_allowed_budget: ResourceBudget::default(),
        });

        // 7. native.file.inspect
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.file.inspect",
                "Native File Inspector",
                "1.0.0",
                "Inspect file metadata, size, line count, binary detection, and cryptographic hash in sandbox",
                true,
                ExecutionClass::IoBounded,
                SideEffectClass::ReadOnly,
                vec!["native.file.inspect".to_string()],
            ),
            default_policy: SandboxPolicy {
                profile: SandboxProfile::Standard,
                filesystem: FilesystemPolicy {
                    mode: FilesystemMode::ReadOnly,
                    allowed_read_roots: vec![],
                    allowed_write_roots: vec![],
                    isolated_workspace: true,
                },
                network: NetworkPolicy {
                    mode: NetworkMode::NoNetwork,
                    allowed_hosts: vec![],
                },
                environment: EnvironmentPolicy::default(),
                process_tree: ProcessTreePolicy::default(),
                output_limits: OutputLimits::default(),
                resource_budget: ResourceBudget::default(),
            },
            max_allowed_budget: ResourceBudget::default(),
        });

        // 8. native.window.inspect
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.window.inspect",
                "Native Window Inspector",
                "1.0.0",
                "Safe read-only window enumeration, focus state, bounds, and process association",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::ReadOnly,
                vec!["native.window.inspect".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 9. native.process.inspect
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.process.inspect",
                "Native Process Inspector",
                "1.0.0",
                "Controlled process metadata enumeration without sensitive host exposure",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::ReadOnly,
                vec!["native.process.inspect".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 10. native.display.inspect
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.display.inspect",
                "Native Display Inspector",
                "1.0.0",
                "Display monitor enumeration, resolution, and coordinate space bounds",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::ReadOnly,
                vec!["native.display.inspect".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 11. native.screen.capture
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.screen.capture",
                "Native Screen Capture",
                "1.0.0",
                "Bounded ephemeral display state capture for visual context inspection",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::ReadOnly,
                vec!["native.screen.capture".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 12. native.clipboard.read
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.clipboard.read",
                "Native Clipboard Reader",
                "1.0.0",
                "Bounded clipboard text reader with strict non-persistence guarantees",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::ReadOnly,
                vec!["native.clipboard.read".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 13. native.clipboard.write
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.clipboard.write",
                "Native Clipboard Writer",
                "1.0.0",
                "Controlled clipboard text writer requiring governance authorization",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::StatefulLocal,
                vec!["native.clipboard.write".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 14. native.input.mouse
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.input.mouse",
                "Native Mouse Input Primitive",
                "1.0.0",
                "Target-validated mouse movements, clicks, and coordinate actions",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::StatefulLocal,
                vec!["native.input.mouse".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });

        // 15. native.input.keyboard
        self.register(SandboxCapabilityContract {
            descriptor: CapabilityDescriptor::new(
                "native.input.keyboard",
                "Native Keyboard Input Primitive",
                "1.0.0",
                "Target-validated typed text and discrete key event execution",
                true,
                ExecutionClass::SystemInspection,
                SideEffectClass::StatefulLocal,
                vec!["native.input.keyboard".to_string()],
            ),
            default_policy: SandboxPolicy::default(),
            max_allowed_budget: ResourceBudget::default(),
        });
    }

    pub fn register(&mut self, contract: SandboxCapabilityContract) {
        self.contracts
            .insert(contract.descriptor.capability_id.clone(), contract);
    }

    pub fn get(&self, capability_id: &str) -> Option<&SandboxCapabilityContract> {
        self.contracts.get(capability_id)
    }

    pub fn list_descriptors(&self) -> Vec<CapabilityDescriptor> {
        self.contracts
            .values()
            .map(|c| c.descriptor.clone())
            .collect()
    }
}
