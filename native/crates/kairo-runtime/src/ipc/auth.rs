use kairo_protocol::{CapabilityDescriptor, ProtocolVersion, CURRENT_PROTOCOL_VERSION};
use serde::{Deserialize, Serialize};
use std::str::FromStr;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct HandshakeRequest {
    pub protocol_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub secret: Option<String>,
    pub client_id: String,
    pub client_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub client_instance_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub nonce: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub requested_capabilities: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakeResponse {
    pub protocol_version: String,
    pub runtime_version: String,
    pub authenticated: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_instance_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability_fingerprint: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub configuration_fingerprint: Option<String>,
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
        self.authenticate_with_session(req, capabilities, runtime_version, None, None, None, None)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn authenticate_with_session(
        &self,
        req: &HandshakeRequest,
        capabilities: Vec<CapabilityDescriptor>,
        runtime_version: &str,
        runtime_instance_id: Option<String>,
        session_id: Option<String>,
        capability_fingerprint: Option<String>,
        configuration_fingerprint: Option<String>,
    ) -> HandshakeResponse {
        let client_ver_res = ProtocolVersion::from_str(&req.protocol_version);
        let negotiated_ver = match client_ver_res {
            Ok(client_ver) => {
                if !ProtocolVersion::CURRENT.is_compatible_with(&client_ver) {
                    return HandshakeResponse {
                        protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
                        runtime_version: runtime_version.to_string(),
                        authenticated: false,
                        runtime_instance_id: None,
                        session_id: None,
                        capability_fingerprint: None,
                        configuration_fingerprint: None,
                        error: Some(format!(
                            "Protocol version mismatch: expected {}, got {}",
                            CURRENT_PROTOCOL_VERSION, req.protocol_version
                        )),
                        capabilities: Vec::new(),
                    };
                }
                client_ver.to_string()
            }
            Err(_) => {
                if req.protocol_version != CURRENT_PROTOCOL_VERSION {
                    return HandshakeResponse {
                        protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
                        runtime_version: runtime_version.to_string(),
                        authenticated: false,
                        runtime_instance_id: None,
                        session_id: None,
                        capability_fingerprint: None,
                        configuration_fingerprint: None,
                        error: Some(format!(
                            "Protocol version mismatch: expected {}, got {}",
                            CURRENT_PROTOCOL_VERSION, req.protocol_version
                        )),
                        capabilities: Vec::new(),
                    };
                }
                CURRENT_PROTOCOL_VERSION.to_string()
            }
        };

        if let Some(ref required_secret) = self.expected_secret {
            let provided = req.secret.as_deref().unwrap_or("");
            let matches =
                ring_like_constant_time_eq(required_secret.as_bytes(), provided.as_bytes());
            if !matches {
                return HandshakeResponse {
                    protocol_version: negotiated_ver,
                    runtime_version: runtime_version.to_string(),
                    authenticated: false,
                    runtime_instance_id: None,
                    session_id: None,
                    capability_fingerprint: None,
                    configuration_fingerprint: None,
                    error: Some("Invalid authentication secret".to_string()),
                    capabilities: Vec::new(),
                };
            }
        }

        HandshakeResponse {
            protocol_version: negotiated_ver,
            runtime_version: runtime_version.to_string(),
            authenticated: true,
            runtime_instance_id,
            session_id,
            capability_fingerprint,
            configuration_fingerprint,
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
