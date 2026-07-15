//! Specialist agents (Phase 3.4).
//!
//! Each agent is a typed descriptor: a [`AgentRole`], a system prompt, a
//! whitelist of tool names it may invoke, and the permission set it maps to on
//! the Python `PermissionRegistry`. Agents are Rust structs that call Aether
//! for LLM reasoning and dispatch tools through
//! [`crate::tools::ToolDispatcher`].

use serde::{Deserialize, Serialize};

/// The ten specialist roles from the roadmap.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AgentRole {
    Planner,
    Researcher,
    Engineer,
    Security,
    Tester,
    Documentation,
    Verification,
    Simulation,
    Memory,
    Recovery,
}

impl AgentRole {
    pub fn as_str(&self) -> &'static str {
        match self {
            AgentRole::Planner => "planner",
            AgentRole::Researcher => "researcher",
            AgentRole::Engineer => "engineer",
            AgentRole::Security => "security",
            AgentRole::Tester => "tester",
            AgentRole::Documentation => "documentation",
            AgentRole::Verification => "verification",
            AgentRole::Simulation => "simulation",
            AgentRole::Memory => "memory",
            AgentRole::Recovery => "recovery",
        }
    }
}

/// A specialist agent descriptor.
#[derive(Debug, Clone)]
pub struct Agent {
    pub role: AgentRole,
    pub name: &'static str,
    pub system_prompt: &'static str,
    pub tools: &'static [&'static str],
    pub permissions: &'static [&'static str],
}

impl Agent {
    /// Whether this agent is permitted to invoke `tool`.
    pub fn can_use(&self, tool: &str) -> bool {
        self.tools.contains(&tool)
    }
}

/// The full roster of specialist agents.
pub fn registry() -> &'static [Agent] {
    &[
        Agent {
            role: AgentRole::Planner,
            name: "Planner",
            system_prompt: "You decompose engineering goals into safe, simulation-first plans.",
            tools: &["knowledge_graph", "hardware", "apis"],
            permissions: &["device.read", "capability.read"],
        },
        Agent {
            role: AgentRole::Researcher,
            name: "Researcher",
            system_prompt: "You gather facts from the knowledge graph and code to answer questions.",
            tools: &["knowledge_graph", "filesystem", "apis"],
            permissions: &["knowledge.read", "fs.read"],
        },
        Agent {
            role: AgentRole::Engineer,
            name: "Engineer",
            system_prompt: "You implement engineering workflows through the HAL and discipline services.",
            tools: &["hardware", "terminal", "filesystem", "sdk"],
            permissions: &["device.connect", "device.read", "device.write", "fs.read", "fs.write", "terminal.execute"],
        },
        Agent {
            role: AgentRole::Security,
            name: "Security",
            system_prompt: "You audit configuration and permissions, flagging risks before action.",
            tools: &["hardware", "knowledge_graph", "terminal"],
            permissions: &["device.read", "knowledge.read"],
        },
        Agent {
            role: AgentRole::Tester,
            name: "Tester",
            system_prompt: "You design and run tests, reporting failures with reproduction steps.",
            tools: &["terminal", "filesystem", "sdk"],
            permissions: &["fs.read", "fs.write", "terminal.execute"],
        },
        Agent {
            role: AgentRole::Documentation,
            name: "Documentation",
            system_prompt: "You write clear, accurate engineering documentation and READMEs.",
            tools: &["filesystem", "knowledge_graph"],
            permissions: &["fs.read", "fs.write", "knowledge.read"],
        },
        Agent {
            role: AgentRole::Verification,
            name: "Verification",
            system_prompt: "You verify signatures, integrity, and compliance of artifacts.",
            tools: &["hardware", "filesystem", "apis"],
            permissions: &["device.read", "fs.read", "capability.read"],
        },
        Agent {
            role: AgentRole::Simulation,
            name: "Simulation",
            system_prompt: "You build digital twins and run failure simulations before execution.",
            tools: &["hardware", "apis"],
            permissions: &["device.read", "capability.read", "capability.execute"],
        },
        Agent {
            role: AgentRole::Memory,
            name: "Memory",
            system_prompt: "You record durable facts and preferences to long-term memory.",
            tools: &["knowledge_graph", "apis"],
            permissions: &["knowledge.write"],
        },
        Agent {
            role: AgentRole::Recovery,
            name: "Recovery",
            system_prompt: "You plan and execute safe device recovery, gated by approval.",
            tools: &["hardware", "terminal"],
            permissions: &["device.connect", "device.write", "device.recover", "terminal.execute"],
        },
    ]
}

/// Look up an agent by role.
pub fn get(role: AgentRole) -> Option<&'static Agent> {
    registry().iter().find(|a| a.role == role)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_agents_have_unique_roles() {
        let roles: Vec<_> = registry().iter().map(|a| a.role).collect();
        let unique = roles.iter().collect::<std::collections::HashSet<_>>();
        assert_eq!(roles.len(), unique.len());
    }

    #[test]
    fn engineer_may_use_terminal() {
        let a = get(AgentRole::Engineer).unwrap();
        assert!(a.can_use("terminal"));
        assert!(!a.can_use("browser"));
    }
}
