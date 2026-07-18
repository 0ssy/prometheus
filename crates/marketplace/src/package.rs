//! Package manifest, metadata and semantic versioning.

use crate::{MarketplaceError, Result};
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use tracing::debug;

/// A semantic version: major.minor.patch with optional pre-release label.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Version {
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
    pub pre: Option<String>,
}

impl Version {
    pub fn new(major: u32, minor: u32, patch: u32) -> Self {
        Self {
            major,
            minor,
            patch,
            pre: None,
        }
    }

    pub fn parse(s: &str) -> Result<Self> {
        let (core, pre) = match s.split_once('-') {
            Some((c, p)) => (c, Some(p.to_string())),
            None => (s, None),
        };
        let parts: Vec<&str> = core.split('.').collect();
        if parts.len() != 3 {
            return Err(MarketplaceError::InvalidVersion(s.to_string()));
        }
        let parse_u = |p: &str| {
            p.parse::<u32>()
                .map_err(|_| MarketplaceError::InvalidVersion(s.to_string()))
        };
        Ok(Self {
            major: parse_u(parts[0])?,
            minor: parse_u(parts[1])?,
            patch: parse_u(parts[2])?,
            pre,
        })
    }

    /// Bump to the next patch version.
    pub fn bump_patch(&self) -> Self {
        Self {
            major: self.major,
            minor: self.minor,
            patch: self.patch + 1,
            pre: None,
        }
    }

    pub fn is_prerelease(&self) -> bool {
        self.pre.is_some()
    }
}

impl PartialOrd for Version {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Version {
    fn cmp(&self, other: &Self) -> Ordering {
        let maj = self.major.cmp(&other.major);
        if maj != Ordering::Equal {
            return maj;
        }
        let min = self.minor.cmp(&other.minor);
        if min != Ordering::Equal {
            return min;
        }
        let pat = self.patch.cmp(&other.patch);
        if pat != Ordering::Equal {
            return pat;
        }
        match (&self.pre, &other.pre) {
            (None, None) => Ordering::Equal,
            (None, Some(_)) => Ordering::Greater,
            (Some(_), None) => Ordering::Less,
            (Some(a), Some(b)) => a.cmp(b),
        }
    }
}

impl std::fmt::Display for Version {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)?;
        if let Some(pre) = &self.pre {
            write!(f, "-{pre}")?;
        }
        Ok(())
    }
}

/// Type of package published to the marketplace.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PackageKind {
    Plugin,
    Driver,
}

/// Package manifest describing a published artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub name: String,
    pub version: Version,
    pub kind: PackageKind,
    pub description: String,
    pub author: String,
    pub license: String,
    pub dependencies: Vec<String>,
    /// SHA256 of the artifact bytes (hex).
    pub artifact_sha256: String,
    pub homepage: Option<String>,
}

impl Manifest {
    pub fn new(
        name: &str,
        version: Version,
        kind: PackageKind,
        artifact_sha256: &str,
    ) -> Self {
        Self {
            name: name.to_string(),
            version,
            kind,
            description: String::new(),
            author: "unknown".into(),
            license: "MIT".into(),
            dependencies: Vec::new(),
            artifact_sha256: artifact_sha256.to_string(),
            homepage: None,
        }
    }

    pub fn validate(&self) -> Result<()> {
        if self.name.trim().is_empty() {
            return Err(MarketplaceError::InvalidManifest("empty name".into()));
        }
        if self.artifact_sha256.len() != 64 {
            return Err(MarketplaceError::InvalidManifest(
                "artifact_sha256 must be 64 hex chars".into(),
            ));
        }
        for d in &self.dependencies {
            if d.trim().is_empty() {
                return Err(MarketplaceError::InvalidManifest(
                    "empty dependency".into(),
                ));
            }
        }
        debug!(name = %self.name, version = %self.version, "manifest validated");
        Ok(())
    }

    pub fn to_json(&self) -> Result<String> {
        serde_json::to_string(self).map_err(|e| {
            MarketplaceError::InvalidManifest(e.to_string())
        })
    }

    pub fn from_json(s: &str) -> Result<Self> {
        let m: Manifest = serde_json::from_str(s)
            .map_err(|e| MarketplaceError::InvalidManifest(e.to_string()))?;
        m.validate()?;
        Ok(m)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_parse_roundtrip() {
        let v = Version::parse("1.2.3").unwrap();
        assert_eq!(v, Version::new(1, 2, 3));
        assert_eq!(v.to_string(), "1.2.3");
    }

    #[test]
    fn version_parse_prerelease() {
        let v = Version::parse("1.0.0-rc1").unwrap();
        assert_eq!(v.pre.as_deref(), Some("rc1"));
        assert!(v.is_prerelease());
    }

    #[test]
    fn version_ordering() {
        assert!(Version::parse("2.0.0").unwrap() > Version::parse("1.9.9").unwrap());
        assert!(Version::parse("1.0.0").unwrap() > Version::parse("1.0.0-alpha").unwrap());
        assert_eq!(Version::parse("1.2.3").unwrap(), Version::parse("1.2.3").unwrap());
    }

    #[test]
    fn version_parse_invalid() {
        assert!(Version::parse("1.2").is_err());
        assert!(Version::parse("x.y.z").is_err());
    }

    #[test]
    fn manifest_validate() {
        let m = Manifest::new("demo", Version::new(0, 1, 0), PackageKind::Plugin,
            "a".repeat(64).as_str());
        assert!(m.validate().is_ok());
    }

    #[test]
    fn manifest_rejects_bad_sha() {
        let m = Manifest::new("demo", Version::new(0, 1, 0), PackageKind::Plugin, "short");
        assert!(m.validate().is_err());
    }

    #[test]
    fn manifest_json_roundtrip() {
        let m = Manifest::new("demo", Version::new(1, 0, 0), PackageKind::Driver,
            "b".repeat(64).as_str())
            .to_json()
            .unwrap();
        let back = Manifest::from_json(&m).unwrap();
        assert_eq!(back.name, "demo");
        assert_eq!(back.kind, PackageKind::Driver);
    }

    #[test]
    fn bump_patch() {
        assert_eq!(Version::new(1, 2, 3).bump_patch(), Version::new(1, 2, 4));
    }
}
