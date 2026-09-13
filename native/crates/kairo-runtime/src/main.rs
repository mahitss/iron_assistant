use clap::Parser;
use kairo_runtime::{
    CancellationRegistry, CapabilityRegistry, IpcServer, LifecycleManager, RequestDispatcher,
    RuntimeConfig, RuntimeMetrics,
};
use std::sync::Arc;
use std::time::Duration;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let config = RuntimeConfig::parse();

    let filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(&config.log_level));

    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer().json())
        .init();

    tracing::info!(
        host = %config.host,
        port = %config.port,
        max_message_bytes = %config.max_message_bytes,
        "Starting Kairo Native Runtime Substrate Daemon..."
    );

    let metrics = RuntimeMetrics::new();
    let cancellation = Arc::new(CancellationRegistry::new());
    let capabilities = Arc::new(CapabilityRegistry::new());
    let lifecycle = LifecycleManager::new(Arc::new(std::sync::atomic::AtomicU32::new(0)));

    // Register capabilities with lifecycle
    lifecycle.set_capabilities(capabilities.ids()).await;

    let dispatcher = RequestDispatcher::new(
        lifecycle.clone(),
        capabilities.clone(),
        cancellation.clone(),
        metrics.clone(),
    );

    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);
    let server = Arc::new(IpcServer::new(
        config.clone(),
        lifecycle.clone(),
        dispatcher,
    ));

    let server_task = tokio::spawn({
        let server = server.clone();
        async move {
            if let Err(e) = server.run(shutdown_rx).await {
                tracing::error!("Server error: {}", e);
            }
        }
    });

    // Wait for termination signal
    tokio::signal::ctrl_c().await?;
    tracing::info!("Received shutdown signal. Entering DRAINING state...");

    // 1. Drain phase: stop accepting new requests
    lifecycle.drain().await;
    let _ = shutdown_tx.send(true);

    // 2. Await active requests drain with timeout
    let drain_timeout = Duration::from_secs(config.shutdown_timeout_secs);
    let drain_start = std::time::Instant::now();

    while drain_start.elapsed() < drain_timeout {
        let meta = lifecycle.metadata().await;
        if meta.active_requests == 0 {
            break;
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }

    // 3. Mark stopped
    lifecycle.stop().await;
    tracing::info!("Runtime stopped cleanly. Exiting.");

    let _ = server_task.await;
    Ok(())
}
