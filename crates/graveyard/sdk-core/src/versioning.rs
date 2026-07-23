//! SDK versioning, a compatibility matrix, and semver compatibility checks.

use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::fmt;
use thiserror::Error;

/// Errors produced while parsing or checking SDK versions.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum VersionError {
    #[error("invalid version string: {0}")]
    InvalidVersion(String),
    #[error("unsupported SDK major version: {0}")]
    UnsupportedMajor(u64),
}

/// A semantic version for the Prometheus SDK API surface.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SdkVersion {
    pub major: u64,
    pub minor: u64,
    pub patch: u64,
}

impl SdkVersion {
    pub const fn new(major: u64, minor: u64, patch: u64) -> Self {
        Self { major, minor, patch }
    }

    /// Parses a `MAJOR.MINOR.PATCH` version string, optionally with a leading
    /// `v`.
    pub fn parse(s: &str) -> Result<Self, VersionError> {
        let s = s.trim().strip_prefix('v').unwrap_or(s);
        let parts: Vec<&str> = s.split('.').collect();
        if parts.len() != 3 {
            return Err(VersionError::InvalidVersion(s.to_string()));
        }
        let parse = |p: &str| p.parse::<u64>().map_err(|_| VersionError::InvalidVersion(s.to_string()));
        Ok(SdkVersion {
            major: parse(parts[0])?,
            minor: parse(parts[1])?,
            patch: parse(parts[2])?,
        })
    }

    /// Renders the canonical `MAJOR.MINOR.PATCH` form.
    pub fn as_str(&self) -> String {
        format!("{}.{}.{}", self.major, self.minor, self.patch)
    }

    /// Returns the minimum SDK version this one is backward compatible with
    /// under semver (same major, minor decrements allowed, patch free).
    pub fn compatible_floor(&self) -> SdkVersion {
        SdkVersion::new(self.major, 0, 0)
    }
}

impl PartialOrd for SdkVersion {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for SdkVersion {
    fn cmp(&self, other: &Self) -> Ordering {
        self.major
            .cmp(&other.major)
            .then_with(|| self.minor.cmp(&other.minor))
            .then_with(|| self.patch.cmp(&other.patch))
    }
}

impl fmt::Display for SdkVersion {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

/// The compatibility verdict between two SDK versions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Compatibility {
    /// Fully compatible: same major, consumer version <= provider version.
    Compatible,
    /// Same major but consumer is newer than provider (may use new APIs).
    ForwardCompatible,
    /// Breaking: differing major versions.
    Incompatible,
}

/// A compatibility matrix mapping an SDK major version to the range of
/// consumer versions it supports.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompatibilityMatrix {
    /// Supported major versions and their minimum minor/patch floors.
    pub supported: Vec<SdkVersion>,
}

impl Default for CompatibilityMatrix {
    fn default() -> Self {
        Self {
            supported: vec![SdkVersion::new(0, 1, 0)],
        }
    }
}

impl CompatibilityMatrix {
    pub fn new(supported: Vec<SdkVersion>) -> Self {
        Self { supported }
    }

    /// Checks whether a consumer built against `consumer` can run against a
    /// host running `provider`, under semver rules.
    pub fn check(&self, provider: SdkVersion, consumer: SdkVersion) -> Compatibility {
        if provider.major != consumer.major {
            return Compatibility::Incompatible;
        }
        if consumer <= provider {
            Compatibility::Compatible
        } else {
            Compatibility::ForwardCompatible
        }
    }

    /// Validates that a version is within the supported matrix.
    pub fn is_supported(&self, v: SdkVersion) -> bool {
        self.supported.iter().any(|s| s.major == v.major && v >= s.compatible_floor())
    }

    /// Returns the maximum supported version, if any.
    pub fn latest(&self) -> Option<SdkVersion> {
        self.supported.iter().copied().max()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_parse_roundtrip() {
        let v = SdkVersion::parse("v0.1.0").unwrap();
        assert_eq!(v, SdkVersion::new(0, 1, 0));
        assert_eq!(v.as_str(), "0.1.0");
    }

    #[test]
    fn version_parse_errors() {
        assert!(SdkVersion::parse("1.2").is_err());
        assert!(SdkVersion::parse("x.y.z").is_err());
    }

    #[test]
    fn version_ordering() {
        assert!(SdkVersion::new(0, 1, 0) < SdkVersion::new(0, 2, 0));
        assert!(SdkVersion::new(1, 0, 0) > SdkVersion::new(0, 9, 9));
    }

    #[test]
    fn compatibility_matrix_checks() {
        let m = CompatibilityMatrix::default();
        assert_eq!(
            m.check(SdkVersion::new(0, 2, 0), SdkVersion::new(0, 1, 0)),
            Compatibility::Compatible
        );
        assert_eq!(
            m.check(SdkVersion::new(0, 1, 0), SdkVersion::new(0, 2, 0)),
            Compatibility::ForwardCompatible
        );
        assert_eq!(
            m.check(SdkVersion::new(1, 0, 0), SdkVersion::new(0, 1, 0)),
            Compatibility::Incompatible
        );
    }

    #[test]
    fn matrix_supported_and_latest() {
        let m = CompatibilityMatrix::default();
        assert!(m.is_supported(SdkVersion::new(0, 1, 0)));
        assert!(m.is_supported(SdkVersion::new(0, 0, 5)));
        assert!(!m.is_supported(SdkVersion::new(2, 0, 0)));
        assert_eq!(m.latest(), Some(SdkVersion::new(0, 1, 0)));
    }

    #[test]
    fn compatible_floor() {
        assert_eq!(SdkVersion::new(0, 5, 3).compatible_floor(), SdkVersion::new(0, 0, 0));
    }
}
