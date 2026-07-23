//! Engineering module interface and agent tool registration for the
//! Prometheus Engineering OS.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Errors produced while registering or invoking engineering tools.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum ExtensionError {
    #[error("tool already registered: {0}")]
    ToolAlreadyRegistered(String),
    #[error("unknown tool: {0}")]
    UnknownTool(String),
    #[error("tool execution failed: {reason}")]
    ExecutionFailed { reason: String },
    #[error("module data store error: {reason}")]
    StoreError { reason: String },
}

/// The category of an engineering module, used for discovery and grouping.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum ModuleKind {
    Analysis,
    Synthesis,
    Optimization,
    Verification,
    Visualization,
    Control,
}

impl ModuleKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            ModuleKind::Analysis => "analysis",
            ModuleKind::Synthesis => "synthesis",
            ModuleKind::Optimization => "optimization",
            ModuleKind::Verification => "verification",
            ModuleKind::Visualization => "visualization",
            ModuleKind::Control => "control",
        }
    }

    pub fn parse(s: &str) -> Option<ModuleKind> {
        match s {
            "analysis" => Some(ModuleKind::Analysis),
            "synthesis" => Some(ModuleKind::Synthesis),
            "optimization" => Some(ModuleKind::Optimization),
            "verification" => Some(ModuleKind::Verification),
            "visualization" => Some(ModuleKind::Visualization),
            "control" => Some(ModuleKind::Control),
            _ => None,
        }
    }
}

/// Declares a tool an engineering module exposes to agents.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ToolRegistration {
    pub name: String,
    pub description: String,
    /// JSON-schema-ish description of the expected input shape.
    pub input_schema: serde_json::Value,
    pub kind: ModuleKind,
}

/// The engineering module interface: a named, kind-tagged provider of tools
/// the Engineering OS agents can invoke.
pub trait EngineeringModule: Send + Sync {
    /// Returns the module's stable identifier.
    fn id(&self) -> &str;

    /// Returns the tools this module contributes to the agent registry.
    fn tools(&self) -> Vec<ToolRegistration>;

    /// Invokes a registered tool by name with a JSON payload.
    fn invoke(&self, tool: &str, payload: &serde_json::Value) -> Result<serde_json::Value, ExtensionError>;
}

/// A registry of agent tools contributed by one or more engineering modules.
///
/// The registry is the single lookup point agents use to discover and run
/// tools across all loaded modules.
#[derive(Debug, Default)]
pub struct ToolRegistry {
    tools: HashMap<String, ToolRegistration>,
    /// Optional module id that contributed each tool, for attribution.
    owner: HashMap<String, String>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers every tool from a module, erroring on duplicate tool names.
    pub fn register_module<M: EngineeringModule>(&mut self, module: &M) -> Result<(), ExtensionError> {
        for tool in module.tools() {
            if self.tools.contains_key(&tool.name) {
                return Err(ExtensionError::ToolAlreadyRegistered(tool.name));
            }
            self.owner.insert(tool.name.clone(), module.id().to_string());
            self.tools.insert(tool.name.clone(), tool);
        }
        tracing::info!(module = %module.id(), "registered engineering module tools");
        Ok(())
    }

    /// Returns the registration metadata for a tool.
    pub fn get(&self, name: &str) -> Option<&ToolRegistration> {
        self.tools.get(name)
    }

    /// Lists all registered tool names.
    pub fn tool_names(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }

    /// Returns the module id that owns a tool, if known.
    pub fn owner_of(&self, name: &str) -> Option<&str> {
        self.owner.get(name).map(String::as_str)
    }
}

/// An in-memory engineering module with injected tool handlers. Useful as a
/// reference implementation and for tests.
pub struct SimpleModule {
    id: String,
    kind: ModuleKind,
    handlers: HashMap<String, Box<dyn Fn(&serde_json::Value) -> Result<serde_json::Value, ExtensionError> + Send + Sync>>,
    registrations: Vec<ToolRegistration>,
}

impl std::fmt::Debug for SimpleModule {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SimpleModule")
            .field("id", &self.id)
            .field("kind", &self.kind)
            .field("registrations", &self.registrations)
            .finish()
    }
}

impl SimpleModule {
    pub fn new(id: &str, kind: ModuleKind) -> Self {
        Self {
            id: id.to_string(),
            kind,
            handlers: HashMap::new(),
            registrations: Vec::new(),
        }
    }

    /// Registers a tool with a synchronous handler closure.
    pub fn add_tool<F>(&mut self, name: &str, description: &str, handler: F)
    where
        F: Fn(&serde_json::Value) -> Result<serde_json::Value, ExtensionError> + Send + Sync + 'static,
    {
        let reg = ToolRegistration {
            name: name.to_string(),
            description: description.to_string(),
            input_schema: serde_json::json!({ "type": "object" }),
            kind: self.kind,
        };
        self.registrations.push(reg);
        self.handlers.insert(name.to_string(), Box::new(handler));
    }
}

impl EngineeringModule for SimpleModule {
    fn id(&self) -> &str {
        &self.id
    }

    fn tools(&self) -> Vec<ToolRegistration> {
        self.registrations.clone()
    }

    fn invoke(&self, tool: &str, payload: &serde_json::Value) -> Result<serde_json::Value, ExtensionError> {
        let handler = self
            .handlers
            .get(tool)
            .ok_or_else(|| ExtensionError::UnknownTool(tool.to_string()))?;
        handler(payload)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn module_kind_roundtrip() {
        assert_eq!(ModuleKind::parse("optimization"), Some(ModuleKind::Optimization));
        assert_eq!(ModuleKind::Optimization.as_str(), "optimization");
        assert_eq!(ModuleKind::parse("nope"), None);
    }

    #[test]
    fn simple_module_invokes_tool() {
        let mut m = SimpleModule::new("mod-1", ModuleKind::Analysis);
        m.add_tool("square", "squares a number", |p| {
            let n = p["n"].as_f64().ok_or_else(|| ExtensionError::ExecutionFailed {
                reason: "missing n".into(),
            })?;
            Ok(serde_json::json!({ "result": n * n }))
        });
        assert_eq!(m.tools().len(), 1);
        let out = m.invoke("square", &serde_json::json!({ "n": 3 })).unwrap();
        assert_eq!(out["result"], 9.0);
        assert!(matches!(m.invoke("missing", &serde_json::json!({})), Err(ExtensionError::UnknownTool(_))));
    }

    #[test]
    fn registry_rejects_duplicate_tools() {
        let mut reg = ToolRegistry::new();
        let mut a = SimpleModule::new("a", ModuleKind::Analysis);
        a.add_tool("dup", "d", |_| Ok(serde_json::json!(null)));
        let mut b = SimpleModule::new("b", ModuleKind::Analysis);
        b.add_tool("dup", "d", |_| Ok(serde_json::json!(null)));
        assert!(reg.register_module(&a).is_ok());
        assert!(matches!(
            reg.register_module(&b),
            Err(ExtensionError::ToolAlreadyRegistered(_))
        ));
        assert_eq!(reg.owner_of("dup"), Some("a"));
        assert_eq!(reg.tool_names(), vec!["dup".to_string()]);
    }
}
