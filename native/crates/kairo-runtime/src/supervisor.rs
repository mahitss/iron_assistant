use futures::FutureExt;
use kairo_protocol::{RuntimeError, RuntimeResponse};
use std::future::Future;
use std::panic::AssertUnwindSafe;

pub async fn run_with_panic_containment<F, Fut>(
    request_id: &str,
    future: F,
) -> Result<RuntimeResponse, RuntimeError>
where
    F: FnOnce() -> Fut,
    Fut: Future<Output = RuntimeResponse>,
{
    match AssertUnwindSafe(future()).catch_unwind().await {
        Ok(response) => Ok(response),
        Err(panic_payload) => {
            let msg = if let Some(s) = panic_payload.downcast_ref::<&str>() {
                *s
            } else if let Some(s) = panic_payload.downcast_ref::<String>() {
                s.as_str()
            } else {
                "Unknown panic occurred in request execution"
            };

            tracing::error!(
                request_id = request_id,
                panic_message = msg,
                "Panic contained at request boundary"
            );

            Err(RuntimeError::internal(
                "CONTAINED_PANIC",
                "Internal execution failure safely contained",
            ))
        }
    }
}
