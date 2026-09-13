use crate::config::RuntimeConfig;
use crate::dispatcher::RequestDispatcher;
use crate::ipc::auth::{HandshakeAuthenticator, HandshakeRequest};
use crate::ipc::framing::LengthPrefixedCodec;
use crate::lifecycle::LifecycleManager;
use futures::{SinkExt, StreamExt};
use kairo_protocol::{RuntimeRequest, RuntimeResponse};
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::{TcpListener, TcpStream};
use tokio_util::codec::Framed;

pub struct IpcServer {
    config: RuntimeConfig,
    lifecycle: Arc<LifecycleManager>,
    dispatcher: RequestDispatcher,
}

impl IpcServer {
    pub fn new(
        config: RuntimeConfig,
        lifecycle: Arc<LifecycleManager>,
        dispatcher: RequestDispatcher,
    ) -> Self {
        Self {
            config,
            lifecycle,
            dispatcher,
        }
    }

    pub async fn run(
        self: Arc<Self>,
        shutdown_rx: tokio::sync::watch::Receiver<bool>,
    ) -> std::io::Result<()> {
        let addr_str = format!("{}:{}", self.config.host, self.config.port);
        let listener = TcpListener::bind(&addr_str).await?;
        tracing::info!("Kairo native runtime listening for IPC on {}", addr_str);

        self.lifecycle.set_ready().await;

        let mut shutdown_watch = shutdown_rx;

        loop {
            tokio::select! {
                accept_res = listener.accept() => {
                    match accept_res {
                        Ok((stream, peer_addr)) => {
                            let this = self.clone();
                            tokio::spawn(async move {
                                if let Err(e) = this.handle_connection(stream, peer_addr).await {
                                    tracing::warn!(peer = %peer_addr, error = %e, "Connection closed with error");
                                }
                            });
                        }
                        Err(e) => {
                            tracing::error!("Error accepting IPC connection: {}", e);
                        }
                    }
                }
                _ = shutdown_watch.changed() => {
                    if *shutdown_watch.borrow() {
                        tracing::info!("IpcServer received shutdown signal. Closing listener.");
                        break;
                    }
                }
            }
        }

        Ok(())
    }

    async fn handle_connection(
        &self,
        stream: TcpStream,
        peer_addr: SocketAddr,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let codec = LengthPrefixedCodec::new(self.config.max_message_bytes);
        let mut framed = Framed::new(stream, codec);

        // 1. Handshake phase
        let handshake_bytes = match framed.next().await {
            Some(Ok(bytes)) => bytes,
            Some(Err(e)) => return Err(Box::new(e)),
            None => return Ok(()),
        };

        let handshake_req: HandshakeRequest = match serde_json::from_slice(&handshake_bytes) {
            Ok(req) => req,
            Err(e) => {
                tracing::warn!(peer = %peer_addr, "Malformed handshake payload");
                return Err(Box::new(e));
            }
        };

        let authenticator = HandshakeAuthenticator::new(self.config.secret.clone());
        let caps = self.dispatcher_capabilities();
        let handshake_resp =
            authenticator.authenticate(&handshake_req, caps, crate::lifecycle::RUNTIME_VERSION);

        let resp_bytes = serde_json::to_vec(&handshake_resp)?;
        framed.send(resp_bytes).await?;

        if !handshake_resp.authenticated {
            tracing::warn!(peer = %peer_addr, "Handshake authentication rejected");
            return Ok(());
        }

        tracing::info!(
            peer = %peer_addr,
            client_id = %handshake_req.client_id,
            "Client successfully authenticated and connected"
        );

        // 2. Request / Response loop
        while let Some(msg_res) = framed.next().await {
            let msg_bytes = match msg_res {
                Ok(bytes) => bytes,
                Err(e) => {
                    tracing::warn!(peer = %peer_addr, error = %e, "Error reading frame from client");
                    break;
                }
            };

            let req: RuntimeRequest = match serde_json::from_slice(&msg_bytes) {
                Ok(r) => r,
                Err(e) => {
                    let err_resp = RuntimeResponse::error(
                        "unknown",
                        kairo_protocol::RuntimeError::invalid_request(
                            "MALFORMED_JSON",
                            format!("Failed to parse JSON request envelope: {e}"),
                        ),
                        None,
                    );
                    let err_bytes = serde_json::to_vec(&err_resp)?;
                    framed.send(err_bytes).await?;
                    continue;
                }
            };

            let resp = self.dispatcher.dispatch(req).await;
            let resp_bytes = serde_json::to_vec(&resp)?;
            framed.send(resp_bytes).await?;
        }

        tracing::debug!(peer = %peer_addr, "Connection finished cleanly");
        Ok(())
    }

    fn dispatcher_capabilities(&self) -> Vec<kairo_protocol::CapabilityDescriptor> {
        let registry = crate::capabilities::CapabilityRegistry::new();
        registry.list()
    }
}
