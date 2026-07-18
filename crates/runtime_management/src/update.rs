//! Rolling update and version management.

use crate::lifecycle::{LifecycleState, Runtime};
use crate::RuntimeError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::info;

/// A versioned release of the runtime software.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Version {
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
}

impl Version {
    pub fn new(major: u32, minor: u32, patch: u32) -> Self {
        Self {
            major,
            minor,
            patch,
        }
    }

    pub fn parse(s: &str) -> Result<Self, RuntimeError> {
        let parts: Vec<&str> = s.split('.').collect();
        if parts.len() != 3 {
            return Err(RuntimeError::VersionNotFound(s.to_string()));
        }
        let p = |x: &str| x.parse::<u32>().map_err(|_| RuntimeError::VersionNotFound(s.to_string()));
        Ok(Self::new(p(parts[0])?, p(parts[1])?, p(parts[2])?))
    }
}

impl std::fmt::Display for Version {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)
    }
}

/// A registered release artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Release {
    pub version: Version,
    pub notes: String,
}

/// Configuration for a rolling update.
#[derive(Debug, Clone)]
pub struct RollingUpdatePlan {
    pub target: Version,
    /// delay between updating each runtime (ms)
    pub batch_delay_ms: u64,
}

/// Manages releases and applies rolling updates to a fleet of runtimes.
#[derive(Debug, Clone, Default)]
pub struct UpdateManager {
    releases: HashMap<Version, Release>,
    current: Option<Version>,
}

impl UpdateManager {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register_release(&mut self, release: Release) {
        self.releases.insert(release.version.clone(), release);
    }

    pub fn set_current(&mut self, version: Version) {
        self.current = Some(version);
    }

    pub fn current(&self) -> Option<&Version> {
        self.current.as_ref()
    }

    pub fn get_release(&self, version: &Version) -> Result<Release, RuntimeError> {
        self.releases
            .get(version)
            .cloned()
            .ok_or_else(|| RuntimeError::VersionNotFound(version.to_string()))
    }

    /// Apply a rolling update to the given fleet. Each runtime is restarted
    /// sequentially (simulated) to the target version if the release exists.
    pub fn rolling_update(
        &self,
        plan: &RollingUpdatePlan,
        fleet: &mut [Runtime],
    ) -> Result<(), RuntimeError> {
        if self.releases.get(&plan.target).is_none() {
            return Err(RuntimeError::VersionNotFound(plan.target.to_string()));
        }
        info!(target = %plan.target, count = fleet.len(), "starting rolling update");
        let total = fleet.len();
        for (i, rt) in fleet.iter_mut().enumerate() {
            if rt.state == LifecycleState::Running {
                rt.stop()?;
            }
            rt.start()?;
            if i + 1 < total {
                std::thread::sleep(std::time::Duration::from_millis(plan.batch_delay_ms));
            }
        }
        Ok(())
    }

    /// Validate that all runtimes reached the expected version (here we mirror
    /// `current` after a successful update).
    pub fn mark_updated(&mut self, version: Version) {
        self.current = Some(version);
    }

    pub fn is_newer(&self, candidate: &Version) -> bool {
        match &self.current {
            None => true,
            Some(cur) => {
                (candidate.major, candidate.minor, candidate.patch)
                    > (cur.major, cur.minor, cur.patch)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fleet(n: usize) -> Vec<Runtime> {
        (0..n).map(|i| {
            let mut r = Runtime::new(&format!("rt-{i}"));
            r.start().unwrap();
            r
        })
        .collect()
    }

    #[test]
    fn version_parse() {
        let v = Version::parse("1.2.3").unwrap();
        assert_eq!(v, Version::new(1, 2, 3));
        assert!(Version::parse("bad").is_err());
    }

    #[test]
    fn is_newer_logic() {
        let mut m = UpdateManager::new();
        m.set_current(Version::new(1, 0, 0));
        assert!(m.is_newer(&Version::new(1, 1, 0)));
        assert!(!m.is_newer(&Version::new(1, 0, 0)));
        assert!(!m.is_newer(&Version::new(0, 9, 9)));
    }

    #[test]
    fn register_and_fetch_release() {
        let mut m = UpdateManager::new();
        m.register_release(Release {
            version: Version::new(2, 0, 0),
            notes: "major".into(),
        });
        assert_eq!(m.get_release(&Version::new(2, 0, 0)).unwrap().notes, "major");
        assert!(m.get_release(&Version::new(9, 9, 9)).is_err());
    }

    #[test]
    fn rolling_update_succeeds() {
        let mut m = UpdateManager::new();
        m.register_release(Release {
            version: Version::new(2, 0, 0),
            notes: String::new(),
        });
        let mut fleet = fleet(3);
        let plan = RollingUpdatePlan {
            target: Version::new(2, 0, 0),
            batch_delay_ms: 0,
        };
        m.rolling_update(&plan, &mut fleet).unwrap();
        assert!(fleet.iter().all(|r| r.is_running()));
        m.mark_updated(Version::new(2, 0, 0));
        assert_eq!(m.current(), Some(&Version::new(2, 0, 0)));
    }

    #[test]
    fn rolling_update_unknown_version_fails() {
        let m = UpdateManager::new();
        let mut fleet = fleet(1);
        let plan = RollingUpdatePlan {
            target: Version::new(9, 9, 9),
            batch_delay_ms: 0,
        };
        assert!(m.rolling_update(&plan, &mut fleet).is_err());
    }
}
