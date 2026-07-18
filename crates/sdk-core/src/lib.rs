//! Prometheus Phase 9 SDK — core types and traits.
//!
//! This crate defines the stable contract surface that third-party and
//! first-party developers build against when extending Prometheus:
//!
//! * [`plugin`] — the plugin manifest, capability/permission model, and the
//!   [`plugin::BasePlugin`] lifecycle trait (`initialize`/`execute`/`shutdown`/
//!   `health`).
//! * [`driver`] — hardware abstraction layer (HAL) trait definitions, the
//!   [`driver::DriverManifest`], and signed driver packaging helpers.
//! * [`extension`] — the engineering module interface and agent tool
//!   registration used by the Engineering OS.
//! * [`versioning`] — SDK versioning, a compatibility matrix, and semver
//!   compatibility checks.
//!
//! All types here are designed to be `serde`-serializable so they can travel
//! across the plugin/distribution boundary unchanged.

pub mod driver;
pub mod extension;
pub mod plugin;
pub mod versioning;

/// The current SDK API version, expressed as a [`versioning::SdkVersion`].
pub const SDK_VERSION: versioning::SdkVersion = versioning::SdkVersion::new(0, 1, 0);

/// Re-exports of the most commonly used items.
pub mod prelude {
    pub use crate::driver::{DriverManifest, Hal};
    pub use crate::extension::{EngineeringModule, ToolRegistration};
    pub use crate::plugin::{BasePlugin, Permission, PluginManifest};
    pub use crate::versioning::{Compatibility, SdkVersion};
}
