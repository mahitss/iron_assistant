use crate::error::RuntimeError;
use serde::{Deserialize, Serialize};

pub const MAX_ALLOWED_DURATION_MS: u64 = 300_000; // 5 minutes max
pub const MAX_ALLOWED_MEMORY_BYTES: u64 = 8 * 1024 * 1024 * 1024; // 8 GiB
pub const MAX_ALLOWED_OUTPUT_BYTES: u64 = 64 * 1024 * 1024; // 64 MiB
pub const MAX_ALLOWED_CONCURRENCY: u32 = 64;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResourceBudget {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_cpu_percent: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_memory_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_execution_time_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_concurrency: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_output_bytes: Option<u64>,
}

impl Default for ResourceBudget {
    fn default() -> Self {
        Self {
            max_cpu_percent: Some(100.0),
            max_memory_bytes: Some(256 * 1024 * 1024), // 256 MiB
            max_execution_time_ms: Some(30_000),       // 30 seconds
            max_concurrency: Some(1),
            max_output_bytes: Some(1024 * 1024), // 1 MiB
        }
    }
}

impl ResourceBudget {
    pub fn validate(&self) -> Result<(), RuntimeError> {
        if let Some(cpu) = self.max_cpu_percent {
            if !cpu.is_finite() || cpu <= 0.0 || cpu > 100.0 {
                return Err(RuntimeError::invalid_request(
                    "INVALID_CPU_BUDGET",
                    format!("max_cpu_percent must be between 0.0 and 100.0, got {cpu}"),
                ));
            }
        }

        if let Some(mem) = self.max_memory_bytes {
            if mem == 0 || mem > MAX_ALLOWED_MEMORY_BYTES {
                return Err(RuntimeError::invalid_request(
                    "INVALID_MEMORY_BUDGET",
                    format!(
                        "max_memory_bytes must be > 0 and <= {MAX_ALLOWED_MEMORY_BYTES}, got {mem}"
                    ),
                ));
            }
        }

        if let Some(duration) = self.max_execution_time_ms {
            if duration == 0 || duration > MAX_ALLOWED_DURATION_MS {
                return Err(RuntimeError::invalid_request(
                    "INVALID_DURATION_BUDGET",
                    format!(
                        "max_execution_time_ms must be > 0 and <= {MAX_ALLOWED_DURATION_MS}, got {duration}"
                    ),
                ));
            }
        }

        if let Some(concurrency) = self.max_concurrency {
            if concurrency == 0 || concurrency > MAX_ALLOWED_CONCURRENCY {
                return Err(RuntimeError::invalid_request(
                    "INVALID_CONCURRENCY_BUDGET",
                    format!(
                        "max_concurrency must be > 0 and <= {MAX_ALLOWED_CONCURRENCY}, got {concurrency}"
                    ),
                ));
            }
        }

        if let Some(out_bytes) = self.max_output_bytes {
            if out_bytes == 0 || out_bytes > MAX_ALLOWED_OUTPUT_BYTES {
                return Err(RuntimeError::invalid_request(
                    "INVALID_OUTPUT_BUDGET",
                    format!(
                        "max_output_bytes must be > 0 and <= {MAX_ALLOWED_OUTPUT_BYTES}, got {out_bytes}"
                    ),
                ));
            }
        }

        Ok(())
    }
}
