use serde::{Deserialize, Serialize};

/// Metadata for a system process observed through native primitives.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProcessMetadata {
    pub pid: u32,
    pub name: String,
    #[serde(default)]
    pub ppid: Option<u32>,
    #[serde(default)]
    pub create_time: Option<u64>,
    #[serde(default = "default_true")]
    pub is_alive: bool,
    #[serde(default)]
    pub memory_bytes: Option<u64>,
    #[serde(default)]
    pub cpu_percent: Option<f32>,
}

fn default_true() -> bool {
    true
}

/// 2D rectangular bounds for a window or display element.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct WindowRect {
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

/// Metadata for an OS window observed through native primitives.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WindowMetadata {
    pub window_id: u64,
    pub title: String,
    pub pid: u32,
    pub process_name: String,
    pub rect: WindowRect,
    pub is_visible: bool,
    pub is_focused: bool,
}

/// Metadata describing a physical or virtual display monitor.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DisplayMetadata {
    pub display_id: u32,
    pub name: String,
    pub width: u32,
    pub height: u32,
    #[serde(default = "default_scale")]
    pub scale_factor: f32,
    #[serde(default)]
    pub is_primary: bool,
}

fn default_scale() -> f32 {
    1.0
}

/// Context binding an input action to an expected target window/process.
/// Prevents ambiguous coordinate-only actions and race condition misfires.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct TargetContext {
    #[serde(default)]
    pub window_id: Option<u64>,
    #[serde(default)]
    pub expected_title: Option<String>,
    #[serde(default)]
    pub expected_pid: Option<u32>,
    #[serde(default)]
    pub expected_process_name: Option<String>,
    #[serde(default)]
    pub coordinate: Option<(i32, i32)>,
    #[serde(default)]
    pub display_id: Option<u32>,
}

/// Mouse buttons supported by native input primitives.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MouseButton {
    Left,
    Right,
    Middle,
}

/// Typed low-level input primitives executed by the native substrate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload")]
pub enum InputPrimitive {
    MouseMove {
        x: i32,
        y: i32,
        target: Option<TargetContext>,
    },
    MouseClick {
        button: MouseButton,
        x: i32,
        y: i32,
        #[serde(default = "default_one")]
        click_count: u32,
        target: Option<TargetContext>,
    },
    MouseButtonAction {
        button: MouseButton,
        is_down: bool,
        target: Option<TargetContext>,
    },
    KeyboardAction {
        key: String,
        is_down: bool,
    },
    TypeText {
        text: String,
        target: Option<TargetContext>,
    },
}

fn default_one() -> u32 {
    1
}

/// Active input state tracked by the native substrate.
/// Used to guarantee safe release of pressed keys/buttons upon cancellation or EmergencyStop.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct InputState {
    pub pressed_keys: Vec<String>,
    pub pressed_buttons: Vec<String>,
    pub active_operation: Option<String>,
}

/// Post-action verification status reflecting state transition confidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum VerificationStatus {
    Confirmed,
    Likely,
    Unverified,
    TargetMismatch,
    Failed,
}

/// Result returned from a native computer interaction primitive.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ComputerOperationResult {
    pub success: bool,
    pub action: String,
    pub target_verified: bool,
    pub verification_status: VerificationStatus,
    pub duration_ms: u64,
    pub error: Option<String>,
    #[serde(default)]
    pub details: serde_json::Value,
}
