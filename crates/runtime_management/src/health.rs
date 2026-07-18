//! Health checks and monitoring.

use crate::lifecycle::{LifecycleState, Runtime};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt::Debug;
use std::time::Instant;
use tracing::warn;
use uuid::Uuid;

/// Health status of a runtime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthStatus {
    Healthy,
    Degraded,
    Unhealthy,
}

impl HealthStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            HealthStatus::Healthy => "healthy",
            HealthStatus::Degraded => "degraded",
            HealthStatus::Unhealthy => "unhealthy",
        }
    }
}

/// A single reported metric/check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheck {
    pub name: String,
    pub status: HealthStatus,
    pub detail: Option<String>,
}

/// A probe that reports a runtime's health.
pub trait Probe: Debug + Send + Sync {
    fn name(&self) -> &'static str;
    fn check(&self, runtime: &Runtime) -> HealthCheck;
}

/// Liveness probe: is the runtime in the Running state?
#[derive(Debug)]
pub struct LivenessProbe;

impl Probe for LivenessProbe {
    fn name(&self) -> &'static str {
        "liveness"
    }

    fn check(&self, runtime: &Runtime) -> HealthCheck {
        let status = if runtime.state == LifecycleState::Running {
            HealthStatus::Healthy
        } else if runtime.state == LifecycleState::Starting {
            HealthStatus::Degraded
        } else {
            HealthStatus::Unhealthy
        };
        HealthCheck {
            name: self.name().into(),
            status,
            detail: Some(runtime.state.as_str().into()),
        }
    }
}

/// Readiness probe: running and recently active (no restart storm).
#[derive(Debug)]
pub struct ReadinessProbe {
    pub max_restarts: u32,
}

impl Probe for ReadinessProbe {
    fn name(&self) -> &'static str {
        "readiness"
    }

    fn check(&self, runtime: &Runtime) -> HealthCheck {
        let (status, detail) = if runtime.state != LifecycleState::Running {
            (HealthStatus::Unhealthy, Some("not running".into()))
        } else if runtime.restart_count > self.max_restarts {
            (
                HealthStatus::Degraded,
                Some(format!("restart storm ({})", runtime.restart_count)),
            )
        } else {
            (HealthStatus::Healthy, None)
        };
        HealthCheck {
            name: self.name().into(),
            status,
            detail,
        }
    }
}

/// Aggregates probes into an overall health view for a runtime.
#[derive(Debug)]
pub struct HealthMonitor {
    probes: Vec<Box<dyn Probe>>,
    last_results: HashMap<Uuid, Vec<HealthCheck>>,
    last_checked: HashMap<Uuid, Instant>,
}

impl HealthMonitor {
    pub fn new() -> Self {
        Self {
            probes: vec![
                Box::new(LivenessProbe),
                Box::new(ReadinessProbe { max_restarts: 5 }),
            ],
            last_results: HashMap::new(),
            last_checked: HashMap::new(),
        }
    }

    pub fn add_probe(&mut self, probe: Box<dyn Probe>) {
        self.probes.push(probe);
    }

    /// Run all probes and return the overall worst status.
    pub fn check(&mut self, runtime: &Runtime) -> (HealthStatus, Vec<HealthCheck>) {
        let mut checks = Vec::new();
        for probe in &self.probes {
            let c = probe.check(runtime);
            if c.status == HealthStatus::Unhealthy {
                warn!(runtime = %runtime.id, probe = c.name, "unhealthy probe");
            }
            checks.push(c);
        }
        let overall = checks
            .iter()
            .map(|c| c.status)
            .max_by_key(|s| match s {
                HealthStatus::Healthy => 0,
                HealthStatus::Degraded => 1,
                HealthStatus::Unhealthy => 2,
            })
            .unwrap_or(HealthStatus::Healthy);
        self.last_results.insert(runtime.id, checks.clone());
        self.last_checked.insert(runtime.id, Instant::now());
        (overall, checks)
    }

    pub fn last_status(&self, id: &Uuid) -> Option<&Vec<HealthCheck>> {
        self.last_results.get(id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn liveness_healthy_when_running() {
        let mut r = Runtime::new("rt");
        r.start().unwrap();
        let c = LivenessProbe.check(&r);
        assert_eq!(c.status, HealthStatus::Healthy);
    }

    #[test]
    fn liveness_unhealthy_when_stopped() {
        let r = Runtime::new("rt");
        let c = LivenessProbe.check(&r);
        assert_eq!(c.status, HealthStatus::Unhealthy);
    }

    #[test]
    fn readiness_degraded_on_restart_storm() {
        let mut r = Runtime::new("rt");
        r.start().unwrap();
        r.restart_count = 10;
        let probe = ReadinessProbe { max_restarts: 5 };
        let c = probe.check(&r);
        assert_eq!(c.status, HealthStatus::Degraded);
    }

    #[test]
    fn monitor_aggregates_to_unhealthy() {
        let r = Runtime::new("rt"); // stopped -> unhealthy liveness
        let mut mon = HealthMonitor::new();
        let (status, checks) = mon.check(&r);
        assert_eq!(status, HealthStatus::Unhealthy);
        assert_eq!(checks.len(), 2);
    }

    #[test]
    fn monitor_healthy_running() {
        let mut r = Runtime::new("rt");
        r.start().unwrap();
        let mut mon = HealthMonitor::new();
        let (status, _) = mon.check(&r);
        assert_eq!(status, HealthStatus::Healthy);
        assert!(mon.last_status(&r.id).is_some());
    }
}
