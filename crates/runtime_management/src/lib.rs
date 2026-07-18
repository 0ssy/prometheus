//! Runtime lifecycle, health checks and rolling updates.
//!
//! - [`lifecycle`] — start/stop/restart state machine for a runtime.
//! - [`health`] — health checks and liveness monitoring.
//! - [`update`] — rolling update orchestration with version management.

pub mod health;
pub mod lifecycle;
pub mod update;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum RuntimeError {
    #[error("invalid state transition: {from} -> {to}")]
    InvalidTransition { from: String, to: String },
    #[error("runtime not running (state: {0})")]
    NotRunning(String),
    #[error("health check failed: {0}")]
    HealthCheck(String),
    #[error("update failed: {0}")]
    Update(String),
    #[error("version {0} not found")]
    VersionNotFound(String),
}

pub type Result<T> = std::result::Result<T, RuntimeError>;
