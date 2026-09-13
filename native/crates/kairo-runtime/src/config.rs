use clap::Parser;

#[derive(Parser, Debug, Clone)]
#[command(
    name = "kairo-runtime",
    about = "Kairo Native Runtime Foundation - Systems Substrate Daemon"
)]
pub struct RuntimeConfig {
    #[arg(long, env = "KAIRO_NATIVE_RUNTIME_HOST", default_value = "127.0.0.1")]
    pub host: String,

    #[arg(long, env = "KAIRO_NATIVE_RUNTIME_PORT", default_value_t = 8788)]
    pub port: u16,

    #[arg(long, env = "KAIRO_NATIVE_RUNTIME_SECRET")]
    pub secret: Option<String>,

    #[arg(long, default_value_t = 1_048_576)]
    pub max_message_bytes: usize,

    #[arg(long, default_value_t = 32)]
    pub max_concurrency: usize,

    #[arg(long, default_value_t = 10)]
    pub shutdown_timeout_secs: u64,

    #[arg(long, env = "KAIRO_LOG_LEVEL", default_value = "info")]
    pub log_level: String,
}

impl Default for RuntimeConfig {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".to_string(),
            port: 8788,
            secret: None,
            max_message_bytes: 1_048_576,
            max_concurrency: 32,
            shutdown_timeout_secs: 10,
            log_level: "info".to_string(),
        }
    }
}
