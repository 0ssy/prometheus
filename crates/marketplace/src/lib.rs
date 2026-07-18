//! Plugin and driver marketplace.
//!
//! - [`registry`] — searchable catalog of published packages.
//! - [`package`] — package manifest, metadata and semantic versioning.
//! - [`verify`] — HMAC-SHA256 signature verification.

pub mod package;
pub mod registry;
pub mod verify;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum MarketplaceError {
    #[error("package {0} not found")]
    NotFound(String),
    #[error("duplicate package {0}")]
    Duplicate(String),
    #[error("invalid manifest: {0}")]
    InvalidManifest(String),
    #[error("version {0} is not a valid semver")]
    InvalidVersion(String),
    #[error("signature verification failed for {0}")]
    Verification(String),
    #[error("registry query error: {0}")]
    Registry(String),
}

pub type Result<T> = std::result::Result<T, MarketplaceError>;
