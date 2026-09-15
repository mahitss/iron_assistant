use crate::budget::ResourceBudget;
use crate::contract::{CapabilityStatus, EnforcementLevel};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ExecutionClass {
    PureCompute,
    IoBounded,
    SystemInspection,
    PrivilegedNative,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SideEffectClass {
    None,
    ReadOnly,
    StatefulLocal,
    ExternalMutation,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CapabilityDescriptor {
    pub capability_id: String,
    pub name: String,
    pub version: String,
    pub description: String,
    pub available: bool,
    pub execution_class: ExecutionClass,
    pub side_effect_class: SideEffectClass,
    pub supported_operations: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default_budget: Option<ResourceBudget>,
    #[serde(default)]
    pub enforcement_level: EnforcementLevel,
    #[serde(default)]
    pub platform: String,
    #[serde(default)]
    pub resource_features: Vec<String>,
    #[serde(default)]
    pub security_features: Vec<String>,
    #[serde(default)]
    pub supported_protocol_versions: Vec<String>,
    #[serde(default)]
    pub status: CapabilityStatus,
}

impl CapabilityDescriptor {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        capability_id: impl Into<String>,
        name: impl Into<String>,
        version: impl Into<String>,
        description: impl Into<String>,
        available: bool,
        execution_class: ExecutionClass,
        side_effect_class: SideEffectClass,
        supported_operations: Vec<String>,
    ) -> Self {
        Self {
            capability_id: capability_id.into(),
            name: name.into(),
            version: version.into(),
            description: description.into(),
            available,
            execution_class,
            side_effect_class,
            supported_operations,
            default_budget: Some(ResourceBudget::default()),
            enforcement_level: EnforcementLevel::HardwareMmuJobObject,
            platform: std::env::consts::OS.to_string(),
            resource_features: vec!["cancellation".into(), "deadlines".into()],
            security_features: vec!["redaction".into(), "panic_containment".into()],
            supported_protocol_versions: vec!["1.0".into(), "1.0.0".into()],
            status: CapabilityStatus::Supported,
        }
    }

    pub fn with_enforcement(
        mut self,
        enforcement_level: EnforcementLevel,
        status: CapabilityStatus,
    ) -> Self {
        self.enforcement_level = enforcement_level;
        self.status = status;
        self
    }
}

impl Default for CapabilityDescriptor {
    fn default() -> Self {
        Self::new(
            "",
            "",
            "1.0.0",
            "",
            true,
            ExecutionClass::PureCompute,
            SideEffectClass::None,
            Vec::new(),
        )
    }
}
