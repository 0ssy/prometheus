//! Prometheus SDK CLI — `prometheus new | pack | verify`.
//!
//! This crate is the Rust equivalent of the Python `prometheus_cli` developer
//! tooling. It is split into three functional modules:
//!
//! * [`scaffold`] — `prometheus new <plugin|agent|driver>` creates a ready-to-
//!   build directory tree with manifest templates and a stub entrypoint.
//! * [`pack`] — `prometheus pack` builds a signed distribution archive (a zip
//!   whose contents are HMAC-SHA256 signed with the developer key).
//! * [`verify`] — `prometheus verify` checks a package's signature and
//!   internal integrity against the developer key.
//!
//! The library is usable both as a binary (see `main.rs`) and programmatically
//! from tests.

pub mod pack;
pub mod scaffold;
pub mod verify;

/// Shared error type for the SDK CLI.
#[derive(Debug, thiserror::Error)]
pub enum CliError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("zip error: {0}")]
    Zip(#[from] zip::result::ZipError),
    #[error("{0}")]
    Other(String),
}

/// Result alias used across the CLI modules.
pub type CliResult<T> = Result<T, CliError>;
