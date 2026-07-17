use std::collections::HashMap;
use std::sync::Mutex;

use crate::agent::{Agent, AgentRole, registry as agent_registry};
use crate::types::{AgentHeartbeat, AgentState};

/// Agent lifecycle state tracker and orchestrator (Phase 3.4).
pub struct AgentCoordinator {
    agents: Mutex<HashMap<AgentRole, AgentState>>,
    heartbeats: Mutex<HashMap<AgentRole, AgentHeartbeat>>,
}

impl AgentCoordinator {
    pub fn new() -> Self {
        Self {
            agents: Mutex::new(HashMap::new()),
            heartbeats: Mutex::new(HashMap::new()),
        }
    }

    /// Spawn an agent, transitioning it to Running.
    pub fn spawn(&self, role: AgentRole) -> AgentState {
        let mut agents = self.agents.lock().expect("agents lock poisoned");
        let state = *agents.entry(role).or_insert(AgentState::Idle);
        let new_state = AgentState::Running;
        agents.insert(role, new_state);
        self.record_heartbeat(role, new_state, None);
        new_state
    }

    /// Pause a running agent.
    pub fn pause(&self, role: AgentRole) -> Result<AgentState, AgentState> {
        let mut agents = self.agents.lock().expect("agents lock poisoned");
        match agents.get(&role) {
            Some(AgentState::Running) => {
                let state = AgentState::Paused;
                agents.insert(role, state);
                self.record_heartbeat(role, state, None);
                Ok(state)
            }
            other => Err(*other.unwrap_or(&AgentState::Idle)),
        }
    }

    /// Resume a paused agent.
    pub fn resume(&self, role: AgentRole) -> Result<AgentState, AgentState> {
        let mut agents = self.agents.lock().expect("agents lock poisoned");
        match agents.get(&role) {
            Some(AgentState::Paused) => {
                let state = AgentState::Running;
                agents.insert(role, state);
                self.record_heartbeat(role, state, None);
                Ok(state)
            }
            other => Err(*other.unwrap_or(&AgentState::Idle)),
        }
    }

    /// Kill an agent.
    pub fn kill(&self, role: AgentRole) -> AgentState {
        let mut agents = self.agents.lock().expect("agents lock poisoned");
        let state = AgentState::Killed;
        agents.insert(role, state);
        self.record_heartbeat(role, state, None);
        state
    }

    /// Restart an agent.
    pub fn restart(&self, role: AgentRole) -> AgentState {
        let mut agents = self.agents.lock().expect("agents lock poisoned");
        agents.insert(role, AgentState::Running);
        self.record_heartbeat(role, AgentState::Running, None);
        AgentState::Running
    }

    /// Current state of an agent.
    pub fn state(&self, role: AgentRole) -> AgentState {
        self.agents
            .lock()
            .expect("agents lock poisoned")
            .get(&role)
            .copied()
            .unwrap_or(AgentState::Idle)
    }

    /// Latest heartbeat for an agent.
    pub fn heartbeat(&self, role: AgentRole) -> Option<AgentHeartbeat> {
        self.heartbeats
            .lock()
            .expect("heartbeats lock poisoned")
            .get(&role)
            .cloned()
    }

    /// All agent heartbeats.
    pub fn all_heartbeats(&self) -> Vec<AgentHeartbeat> {
        self.heartbeats
            .lock()
            .expect("heartbeats lock poisoned")
            .values()
            .cloned()
            .collect()
    }

    /// List all registered agents and their current states.
    pub fn list(&self) -> Vec<(AgentRole, AgentState)> {
        let agents = self.agents.lock().expect("agents lock poisoned");
        agent_registry()
            .iter()
            .map(|a| (a.role, agents.get(&a.role).copied().unwrap_or(AgentState::Idle)))
            .collect()
    }

    /// Update an agent's task and last-seen timestamp.
    pub fn record_heartbeat(&self, role: AgentRole, state: AgentState, task: Option<String>) {
        let mut heartbeats = self.heartbeats.lock().expect("heartbeats lock poisoned");
        heartbeats.insert(
            role,
            AgentHeartbeat {
                role,
                state,
                last_seen: chrono::Utc::now().to_rfc3339(),
                task,
            },
        );
    }

    /// Dispatch parallel tool calls for a set of agents.
    pub fn dispatch_parallel(
        &self,
        _roles: &[AgentRole],
        _tool: &str,
        _args: serde_json::Value,
    ) -> Vec<(AgentRole, Result<serde_json::Value, crate::error::AetherError>)> {
        let _agents = self.agents.lock().expect("agents lock poisoned");
        _roles
            .iter()
            .map(|role| (*role, Err(crate::error::AetherError::Provider("not implemented".to_string()))))
            .collect()
    }
}

impl Default for AgentCoordinator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn spawn_sets_running() {
        let c = AgentCoordinator::new();
        assert_eq!(c.spawn(AgentRole::Engineer), AgentState::Running);
    }

    #[test]
    fn pause_resume_cycle() {
        let c = AgentCoordinator::new();
        c.spawn(AgentRole::Engineer);
        assert_eq!(c.pause(AgentRole::Engineer), Ok(AgentState::Paused));
        assert_eq!(c.resume(AgentRole::Engineer), Ok(AgentState::Running));
    }

    #[test]
    fn kill_sets_killed() {
        let c = AgentCoordinator::new();
        c.spawn(AgentRole::Engineer);
        assert_eq!(c.kill(AgentRole::Engineer), AgentState::Killed);
    }

    #[test]
    fn restart_sets_running() {
        let c = AgentCoordinator::new();
        c.spawn(AgentRole::Engineer);
        c.kill(AgentRole::Engineer);
        assert_eq!(c.restart(AgentRole::Engineer), AgentState::Running);
    }

    #[test]
    fn heartbeat_records_timestamp() {
        let c = AgentCoordinator::new();
        c.spawn(AgentRole::Engineer);
        let hb = c.heartbeat(AgentRole::Engineer).unwrap();
        assert_eq!(hb.state, AgentState::Running);
        assert!(hb.last_seen.contains('Z') || hb.last_seen.contains('+'));
    }

    #[test]
    fn list_returns_all_roles() {
        let c = AgentCoordinator::new();
        let all = c.list();
        assert_eq!(all.len(), 10);
    }
}
