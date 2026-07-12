//! Aggregated runtime health: providers plus the Prometheus backend.

use std::time::Instant;

use reqwest::Client;

use crate::manager::ProviderManager;
use crate::types::{ProviderHealth, RuntimeHealth};

/// Probe all registered providers and the Prometheus backend at `backend_url`
/// (e.g. `http://127.0.0.1:8000`), returning an aggregated snapshot.
///
/// Provider and backend probes never hard-fail: unhealthy targets are reported
/// as `ProviderHealth { ok: false, .. }` rather than as an error, so the
/// command surface can return a full picture even when parts are down.
pub async fn check_runtime(manager: &ProviderManager, backend_url: &str) -> RuntimeHealth {
    let mut providers = Vec::new();
    for (_id, health) in manager.health_all().await {
        providers.push(health);
    }

    let backend = backend_health(backend_url).await;

    RuntimeHealth { providers, backend }
}

/// Liveness probe against the Prometheus FastAPI `/health` endpoint.
///
/// Reuses the existing backend surface instead of inventing new IPC; `ok` is
/// true iff the endpoint returns 2xx, and the round-trip latency is recorded.
pub async fn backend_health(backend_url: &str) -> ProviderHealth {
    let client = Client::new();
    let url = format!("{backend_url}/health");
    let start = Instant::now();
    match client.get(&url).send().await {
        Ok(resp) => {
            let latency = start.elapsed().as_millis();
            if resp.status().is_success() {
                ProviderHealth::ok(latency)
            } else {
                ProviderHealth::err(format!("backend /health returned {}", resp.status()))
            }
        }
        Err(e) => ProviderHealth::err(format!("backend unreachable: {e}")),
    }
}
