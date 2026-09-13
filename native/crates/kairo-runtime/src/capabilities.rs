use kairo_protocol::{CapabilityDescriptor, ExecutionClass, ResourceBudget, SideEffectClass};
use std::collections::HashMap;

pub struct CapabilityRegistry {
    capabilities: HashMap<String, CapabilityDescriptor>,
}

impl Default for CapabilityRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl CapabilityRegistry {
    pub fn new() -> Self {
        let mut registry = Self {
            capabilities: HashMap::new(),
        };
        registry.register_builtins();
        registry
    }

    fn register_builtins(&mut self) {
        self.register(CapabilityDescriptor {
            capability_id: "sys.ping".to_string(),
            name: "System Ping".to_string(),
            version: "1.0.0".to_string(),
            description: "High-speed loopback ping and latency probe".to_string(),
            available: true,
            execution_class: ExecutionClass::PureCompute,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sys.ping".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sys.health".to_string(),
            name: "System Health".to_string(),
            version: "1.0.0".to_string(),
            description: "Query native runtime health and subsystem status".to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sys.health".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sys.info".to_string(),
            name: "System Info".to_string(),
            version: "1.0.0".to_string(),
            description: "Query host platform architecture, OS, and uptime metadata".to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sys.info".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sys.metrics".to_string(),
            name: "Runtime Metrics".to_string(),
            version: "1.0.0".to_string(),
            description: "Query native telemetry, request counters, and latency statistics"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sys.metrics".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sys.sleep".to_string(),
            name: "System Sleep (Testing Probe)".to_string(),
            version: "1.0.0".to_string(),
            description:
                "Controlled delay probe to test deadline enforcement and cooperative cancellation"
                    .to_string(),
            available: true,
            execution_class: ExecutionClass::PureCompute,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sys.sleep".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sandbox.preflight".to_string(),
            name: "Sandbox Preflight & Dry Run".to_string(),
            version: "1.0.0".to_string(),
            description:
                "Dry-run simulation calculating effective sandbox policy and validating constraints"
                    .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sandbox.preflight".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sandbox.echo".to_string(),
            name: "Sandbox Safe Echo".to_string(),
            version: "1.0.0".to_string(),
            description:
                "Deterministic echo capability for testing argument isolation and output capture"
                    .to_string(),
            available: true,
            execution_class: ExecutionClass::PureCompute,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sandbox.echo".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sandbox.hash".to_string(),
            name: "Sandbox Cryptographic Hash".to_string(),
            version: "1.0.0".to_string(),
            description:
                "Pure-compute cryptographic SHA-256 computation on payload or workspace file"
                    .to_string(),
            available: true,
            execution_class: ExecutionClass::PureCompute,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sandbox.hash".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sandbox.probe".to_string(),
            name: "Sandbox Security & Adversarial Test Probe".to_string(),
            version: "1.0.0".to_string(),
            description:
                "Deterministic probe to test timeouts, cooperative cancellation, output flood, and child containment"
                    .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::None,
            supported_operations: vec!["sandbox.probe".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        self.register(CapabilityDescriptor {
            capability_id: "sandbox.execute".to_string(),
            name: "Sandbox Governed Execution".to_string(),
            version: "1.0.0".to_string(),
            description:
                "Secure governed execution for authorized capability workloads within isolated boundaries"
                    .to_string(),
            available: true,
            execution_class: ExecutionClass::PrivilegedNative,
            side_effect_class: SideEffectClass::StatefulLocal,
            supported_operations: vec!["sandbox.execute".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 9. native.window.inspect
        self.register(CapabilityDescriptor {
            capability_id: "native.window.inspect".to_string(),
            name: "Native Window Inspector".to_string(),
            version: "1.0.0".to_string(),
            description: "Enumerate active host windows, titles, PIDs, geometry, and focus state"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::ReadOnly,
            supported_operations: vec!["native.window.inspect".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 10. native.process.inspect
        self.register(CapabilityDescriptor {
            capability_id: "native.process.inspect".to_string(),
            name: "Native Process Inspector".to_string(),
            version: "1.0.0".to_string(),
            description: "Enumerate host processes, identities, parentage, and lifecycle state"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::ReadOnly,
            supported_operations: vec!["native.process.inspect".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 11. native.display.inspect
        self.register(CapabilityDescriptor {
            capability_id: "native.display.inspect".to_string(),
            name: "Native Display Inspector".to_string(),
            version: "1.0.0".to_string(),
            description: "Display monitor enumeration, resolution, and coordinate space bounds"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::ReadOnly,
            supported_operations: vec!["native.display.inspect".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 12. native.screen.capture
        self.register(CapabilityDescriptor {
            capability_id: "native.screen.capture".to_string(),
            name: "Native Screen Capture".to_string(),
            version: "1.0.0".to_string(),
            description: "Bounded ephemeral display state capture for visual context inspection"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::ReadOnly,
            supported_operations: vec!["native.screen.capture".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 13. native.clipboard.read
        self.register(CapabilityDescriptor {
            capability_id: "native.clipboard.read".to_string(),
            name: "Native Clipboard Reader".to_string(),
            version: "1.0.0".to_string(),
            description: "Bounded clipboard text reader with strict non-persistence guarantees"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::ReadOnly,
            supported_operations: vec!["native.clipboard.read".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 14. native.clipboard.write
        self.register(CapabilityDescriptor {
            capability_id: "native.clipboard.write".to_string(),
            name: "Native Clipboard Writer".to_string(),
            version: "1.0.0".to_string(),
            description: "Controlled clipboard text writer requiring governance authorization"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::StatefulLocal,
            supported_operations: vec!["native.clipboard.write".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 15. native.input.mouse
        self.register(CapabilityDescriptor {
            capability_id: "native.input.mouse".to_string(),
            name: "Native Mouse Input Primitive".to_string(),
            version: "1.0.0".to_string(),
            description: "Target-validated mouse movements, clicks, and coordinate actions"
                .to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::StatefulLocal,
            supported_operations: vec!["native.input.mouse".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });

        // 16. native.input.keyboard
        self.register(CapabilityDescriptor {
            capability_id: "native.input.keyboard".to_string(),
            name: "Native Keyboard Input Primitive".to_string(),
            version: "1.0.0".to_string(),
            description: "Target-validated typed text and discrete key event execution".to_string(),
            available: true,
            execution_class: ExecutionClass::SystemInspection,
            side_effect_class: SideEffectClass::StatefulLocal,
            supported_operations: vec!["native.input.keyboard".to_string()],
            default_budget: Some(ResourceBudget::default()),
        });
    }

    pub fn register(&mut self, cap: CapabilityDescriptor) {
        self.capabilities.insert(cap.capability_id.clone(), cap);
    }

    pub fn get(&self, capability_id: &str) -> Option<&CapabilityDescriptor> {
        self.capabilities.get(capability_id)
    }

    pub fn list(&self) -> Vec<CapabilityDescriptor> {
        self.capabilities.values().cloned().collect()
    }

    pub fn ids(&self) -> Vec<String> {
        self.capabilities.keys().cloned().collect()
    }
}
