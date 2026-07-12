//! Error types for the Aether AI Runtime.

use thiserror::Error;

/// Errors surfaced by the runtime and exposed to Tauri commands (`String`).
#[derive(Debug, Error)]
pub enum AetherError {
    #[error("http request failed: {0}")]
    Http(#[from] reqwest::Error),

    #[error("provider error: {0}")]
    Provider(String),

    #[error("no provider registered with id '{0}'")]
    NotFound(String),

    #[error("prometheus backend unreachable: {0}")]
    BackendUnreachable(String),

    #[error("json (de)serialization failed: {0}")]
    Json(#[from] serde_json::Error),
}
