use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio_util::sync::CancellationToken;

#[derive(Debug, Clone, Default)]
pub struct CancellationRegistry {
    tokens: Arc<RwLock<HashMap<String, CancellationToken>>>,
}

impl CancellationRegistry {
    pub fn new() -> Self {
        Self {
            tokens: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn register(&self, cancellation_id: &str) -> CancellationToken {
        let mut map = self.tokens.write().await;
        if let Some(token) = map.get(cancellation_id) {
            token.clone()
        } else {
            let token = CancellationToken::new();
            map.insert(cancellation_id.to_string(), token.clone());
            token
        }
    }

    pub async fn cancel(&self, cancellation_id: &str) -> bool {
        let map = self.tokens.read().await;
        if let Some(token) = map.get(cancellation_id) {
            token.cancel();
            true
        } else {
            false
        }
    }

    pub async fn remove(&self, cancellation_id: &str) {
        let mut map = self.tokens.write().await;
        map.remove(cancellation_id);
    }
}
