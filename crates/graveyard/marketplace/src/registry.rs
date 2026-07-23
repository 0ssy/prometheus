//! Plugin/driver registry with search and discovery.

use crate::package::{Manifest, PackageKind, Version};
use crate::{MarketplaceError, Result};
use std::collections::BTreeMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, info};

/// A published package entry holding all versions of a package name.
#[derive(Debug, Clone)]
pub struct PackageEntry {
    pub manifest: Manifest,
}

/// Search filter for registry queries.
#[derive(Debug, Clone, Default)]
pub struct SearchQuery {
    pub name_contains: Option<String>,
    pub kind: Option<PackageKind>,
    pub author: Option<String>,
}

/// A searchable registry of published packages.
#[derive(Debug, Clone, Default)]
pub struct Registry {
    packages: Arc<RwLock<BTreeMap<String, Vec<Manifest>>>>,
}

impl Registry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Publish (or add a new version of) a package.
    pub async fn publish(&self, manifest: Manifest) -> Result<()> {
        manifest.validate()?;
        let mut guard = self.packages.write().await;
        let list = guard.entry(manifest.name.clone()).or_default();
        if list.iter().any(|m| m.version == manifest.version) {
            return Err(MarketplaceError::Duplicate(format!(
                "{}@{}",
                manifest.name, manifest.version
            )));
        }
        info!(name = %manifest.name, version = %manifest.version, "published package");
        list.push(manifest);
        list.sort_by(|a, b| b.version.cmp(&a.version));
        Ok(())
    }

    /// Fetch the latest version of a package.
    pub async fn get_latest(&self, name: &str) -> Result<Manifest> {
        let guard = self.packages.read().await;
        let list = guard
            .get(name)
            .ok_or_else(|| MarketplaceError::NotFound(name.to_string()))?;
        list.first()
            .cloned()
            .ok_or_else(|| MarketplaceError::NotFound(name.to_string()))
    }

    /// Fetch a specific version of a package.
    pub async fn get_version(&self, name: &str, version: &Version) -> Result<Manifest> {
        let guard = self.packages.read().await;
        let list = guard
            .get(name)
            .ok_or_else(|| MarketplaceError::NotFound(name.to_string()))?;
        list.iter()
            .find(|m| &m.version == version)
            .cloned()
            .ok_or_else(|| MarketplaceError::NotFound(format!("{name}@{version}")))
    }

    /// Search the registry using a query.
    pub async fn search(&self, query: &SearchQuery) -> Vec<Manifest> {
        let guard = self.packages.read().await;
        let mut out = Vec::new();
        for list in guard.values() {
            for m in list {
                if let Some(k) = query.kind {
                    if m.kind != k {
                        continue;
                    }
                }
                if let Some(a) = &query.author {
                    if &m.author != a {
                        continue;
                    }
                }
                if let Some(sub) = &query.name_contains {
                    if !m.name.to_lowercase().contains(&sub.to_lowercase()) {
                        continue;
                    }
                }
                out.push(m.clone());
            }
        }
        debug!(count = out.len(), "registry search");
        out
    }

    /// List all distinct package names. Latest version per name.
    pub async fn list_names(&self) -> Vec<String> {
        let guard = self.packages.read().await;
        guard.keys().cloned().collect()
    }

    pub async fn count(&self) -> usize {
        self.packages.read().await.len()
    }

    /// Unpublish a specific version.
    pub async fn unpublish(&self, name: &str, version: &Version) -> Result<()> {
        let mut guard = self.packages.write().await;
        let list = guard
            .get_mut(name)
            .ok_or_else(|| MarketplaceError::NotFound(name.to_string()))?;
        let before = list.len();
        list.retain(|m| &m.version != version);
        if list.len() == before {
            return Err(MarketplaceError::NotFound(format!("{name}@{version}")));
        }
        if list.is_empty() {
            guard.remove(name);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::Version;

    fn manifest(name: &str, major: u32, kind: PackageKind) -> Manifest {
        Manifest::new(name, Version::new(major, 0, 0), kind, "c".repeat(64).as_str())
    }

    #[tokio::test]
    async fn publish_and_get() {
        let r = Registry::new();
        r.publish(manifest("alpha", 1, PackageKind::Plugin)).await.unwrap();
        assert_eq!(r.count().await, 1);
        let got = r.get_latest("alpha").await.unwrap();
        assert_eq!(got.version, Version::new(1, 0, 0));
    }

    #[tokio::test]
    async fn duplicate_version_rejected() {
        let r = Registry::new();
        r.publish(manifest("a", 1, PackageKind::Driver)).await.unwrap();
        assert!(r.publish(manifest("a", 1, PackageKind::Driver)).await.is_err());
    }

    #[tokio::test]
    async fn latest_is_highest_version() {
        let r = Registry::new();
        r.publish(manifest("a", 1, PackageKind::Plugin)).await.unwrap();
        r.publish(manifest("a", 3, PackageKind::Plugin)).await.unwrap();
        r.publish(manifest("a", 2, PackageKind::Plugin)).await.unwrap();
        assert_eq!(r.get_latest("a").await.unwrap().version, Version::new(3, 0, 0));
    }

    #[tokio::test]
    async fn search_by_kind_and_name() {
        let r = Registry::new();
        r.publish(manifest("prom-usb", 1, PackageKind::Driver)).await.unwrap();
        r.publish(manifest("prom-ble", 1, PackageKind::Driver)).await.unwrap();
        r.publish(manifest("demo-plugin", 1, PackageKind::Plugin)).await.unwrap();

        let drivers = r.search(&SearchQuery { kind: Some(PackageKind::Driver), ..Default::default() }).await;
        assert_eq!(drivers.len(), 2);

        let usb = r.search(&SearchQuery { name_contains: Some("usb".into()), ..Default::default() }).await;
        assert_eq!(usb.len(), 1);
        assert_eq!(usb[0].name, "prom-usb");
    }

    #[tokio::test]
    async fn get_specific_version() {
        let r = Registry::new();
        r.publish(manifest("a", 1, PackageKind::Plugin)).await.unwrap();
        r.publish(manifest("a", 2, PackageKind::Plugin)).await.unwrap();
        let v2 = r.get_version("a", &Version::new(2, 0, 0)).await.unwrap();
        assert_eq!(v2.version, Version::new(2, 0, 0));
        assert!(r.get_version("a", &Version::new(9, 0, 0)).await.is_err());
    }

    #[tokio::test]
    async fn unpublish_version() {
        let r = Registry::new();
        r.publish(manifest("a", 1, PackageKind::Plugin)).await.unwrap();
        r.publish(manifest("a", 2, PackageKind::Plugin)).await.unwrap();
        r.unpublish("a", &Version::new(1, 0, 0)).await.unwrap();
        assert_eq!(r.get_latest("a").await.unwrap().version, Version::new(2, 0, 0));
        // publishing the same version again should now succeed
        r.publish(manifest("a", 1, PackageKind::Plugin)).await.unwrap();
    }
}
