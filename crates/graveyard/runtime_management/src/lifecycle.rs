//! Runtime start/stop/restart lifecycle.

use crate::RuntimeError;
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};
use tracing::{debug, info, warn};
use uuid::Uuid;

/// Lifecycle states of a managed runtime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LifecycleState {
    Stopped,
    Starting,
    Running,
    Stopping,
    Failed,
}

impl LifecycleState {
    pub fn as_str(&self) -> &'static str {
        match self {
            LifecycleState::Stopped => "stopped",
            LifecycleState::Starting => "starting",
            LifecycleState::Running => "running",
            LifecycleState::Stopping => "stopping",
            LifecycleState::Failed => "failed",
        }
    }
}

/// A managed runtime instance.
#[derive(Debug, Clone)]
pub struct Runtime {
    pub id: Uuid,
    pub name: String,
    pub state: LifecycleState,
    pub started_at: Option<Instant>,
    pub restart_count: u32,
}

impl Runtime {
    pub fn new(name: &str) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.to_string(),
            state: LifecycleState::Stopped,
            started_at: None,
            restart_count: 0,
        }
    }

    fn transition(&mut self, target: LifecycleState) -> Result<(), RuntimeError> {
        let allowed = matches!(
            (self.state, target),
            (LifecycleState::Stopped, LifecycleState::Starting)
                | (LifecycleState::Starting, LifecycleState::Running)
                | (LifecycleState::Starting, LifecycleState::Failed)
                | (LifecycleState::Running, LifecycleState::Stopping)
                | (LifecycleState::Running, LifecycleState::Failed)
                | (LifecycleState::Stopping, LifecycleState::Stopped)
                | (LifecycleState::Failed, LifecycleState::Stopped)
                | (LifecycleState::Failed, LifecycleState::Starting)
        );
        if !allowed {
            return Err(RuntimeError::InvalidTransition {
                from: self.state.as_str().into(),
                to: target.as_str().into(),
            });
        }
        self.state = target;
        Ok(())
    }

    pub fn start(&mut self) -> Result<(), RuntimeError> {
        self.transition(LifecycleState::Starting)?;
        self.started_at = Some(Instant::now());
        self.transition(LifecycleState::Running)?;
        info!(id = %self.id, name = %self.name, "runtime started");
        Ok(())
    }

    pub fn stop(&mut self) -> Result<(), RuntimeError> {
        self.transition(LifecycleState::Stopping)?;
        self.transition(LifecycleState::Stopped)?;
        self.started_at = None;
        info!(id = %self.id, name = %self.name, "runtime stopped");
        Ok(())
    }

    /// Restart: stop then start, incrementing the restart counter.
    pub fn restart(&mut self) -> Result<(), RuntimeError> {
        if self.state != LifecycleState::Running {
            return Err(RuntimeError::NotRunning(self.state.as_str().into()));
        }
        self.stop()?;
        self.restart_count += 1;
        self.start()?;
        debug!(id = %self.id, restarts = self.restart_count, "runtime restarted");
        Ok(())
    }

    pub fn fail(&mut self) -> Result<(), RuntimeError> {
        self.transition(LifecycleState::Failed)?;
        warn!(id = %self.id, "runtime marked failed");
        Ok(())
    }

    pub fn uptime(&self) -> Option<Duration> {
        self.started_at.map(|t| t.elapsed())
    }

    pub fn is_running(&self) -> bool {
        self.state == LifecycleState::Running
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn start_stop_cycle() {
        let mut r = Runtime::new("rt");
        assert_eq!(r.state, LifecycleState::Stopped);
        r.start().unwrap();
        assert!(r.is_running());
        r.stop().unwrap();
        assert_eq!(r.state, LifecycleState::Stopped);
    }

    #[test]
    fn invalid_transition_rejected() {
        let mut r = Runtime::new("rt");
        assert!(r.stop().is_err());
        assert!(r.restart().is_err());
    }

    #[test]
    fn restart_increments() {
        let mut r = Runtime::new("rt");
        r.start().unwrap();
        r.restart().unwrap();
        assert_eq!(r.restart_count, 1);
        assert!(r.is_running());
    }

    #[test]
    fn fail_transition() {
        let mut r = Runtime::new("rt");
        r.start().unwrap();
        r.fail().unwrap();
        assert_eq!(r.state, LifecycleState::Failed);
        // can recover from failed
        r.transition(LifecycleState::Stopped).unwrap();
        r.start().unwrap();
    }

    #[test]
    fn uptime_tracked() {
        let mut r = Runtime::new("rt");
        r.start().unwrap();
        std::thread::sleep(Duration::from_millis(5));
        assert!(r.uptime().unwrap() >= Duration::from_millis(5));
    }
}
