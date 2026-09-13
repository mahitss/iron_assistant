use kairo_protocol::{CapabilityDescriptor, CURRENT_PROTOCOL_VERSION};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakeRequest {
    pub protocol_version: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub secret: Option<String>,
    pub client_id: String,
    pub client_version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakeResponse {
    pub protocol_version: String,
    pub runtime_version: String,
    pub authenticated: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    pub capabilities: Vec<CapabilityDescriptor>,
}

pub struct HandshakeAuthenticator {
    expected_secret: Option<String>,
}

impl HandshakeAuthenticator {
    pub fn new(expected_secret: Option<String>) -> Self {
        Self { expected_secret }
    }

    pub fn authenticate(
        &self,
        req: &HandshakeRequest,
        capabilities: Vec<CapabilityDescriptor>,
        runtime_version: &str,
    ) -> HandshakeResponse {
        if req.protocol_version != CURRENT_PROTOCOL_VERSION {
            return HandshakeResponse {
                protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
                runtime_version: runtime_version.to_string(),
                authenticated: false,
                error: Some(format!(
                    "Protocol version mismatch: expected {}, got {}",
                    CURRENT_PROTOCOL_VERSION, req.protocol_version
                )),
                capabilities: Vec::new(),
            };
        }

        if let Some(ref required_secret) = self.expected_secret {
            let provided = req.secret.as_deref().unwrap_or("");
            // Constant time comparison
            let matches =
                ring_like_constant_time_eq(required_secret.as_bytes(), provided.as_bytes());
            if !matches {
                return HandshakeResponse {
                    protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
                    runtime_version: runtime_version.to_string(),
                    authenticated: false,
                    error: Some("Invalid authentication secret".to_string()),
                    capabilities: Vec::new(),
                };
            }
        }

        HandshakeResponse {
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            runtime_version: runtime_version.to_string(),
            authenticated: true,
            error: None,
            capabilities,
        }
    }
}

fn ring_like_constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut result = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        result |= x ^ y;
    }
    result == 0
}
