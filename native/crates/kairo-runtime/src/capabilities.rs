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
