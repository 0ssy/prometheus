//! Plugin model: manifest, capability/permission model, and the
//! [`BasePlugin`] lifecycle trait.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use thiserror::Error;

/// Errors produced while working with plugin manifests and permissions.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum PluginError {
    #[error("unknown permission: {0}")]
    UnknownPermission(String),
    #[error("permission not granted: {0}")]
    PermissionDenied(Permission),
    #[error("plugin {0} is not initialized")]
    NotInitialized(String),
    #[error("plugin {0} is already initialized")]
    AlreadyInitialized(String),
    #[error("plugin health check failed: {reason}")]
    HealthCheckFailed { reason: String },
    #[error("plugin execution failed: {reason}")]
    ExecutionFailed { reason: String },
}

/// A capability a plugin advertises in its manifest.
///
/// Capabilities are the coarse-grained *what* a plugin does; [`Permission`]s
/// are the fine-grained *access* it requires.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Capability {
    /// Reads telemetry / sensor data.
    TelemetryRead,
    /// Writes commands to actuators or devices.
    DeviceControl,
    /// Registers analysis tools usable by engineering agents.
    AnalysisTool,
    /// Provides an optimization / solver backend.
    Optimization,
    /// Supplies a UI panel or dashboard widget.
    UiExtension,
    /// Runs an autonomous background loop.
    AutonomousLoop,
}

impl Capability {
    pub fn as_str(&self) -> &'static str {
        match self {
            Capability::TelemetryRead => "telemetry-read",
            Capability::DeviceControl => "device-control",
            Capability::AnalysisTool => "analysis-tool",
            Capability::Optimization => "optimization",
            Capability::UiExtension => "ui-extension",
            Capability::AutonomousLoop => "autonomous-loop",
        }
    }

    /// Parses a capability from its kebab-case string form.
    pub fn parse(s: &str) -> Result<Capability, PluginError> {
        match s {
            "telemetry-read" => Ok(Capability::TelemetryRead),
            "device-control" => Ok(Capability::DeviceControl),
            "analysis-tool" => Ok(Capability::AnalysisTool),
            "optimization" => Ok(Capability::Optimization),
            "ui-extension" => Ok(Capability::UiExtension),
            "autonomous-loop" => Ok(Capability::AutonomousLoop),
            other => Err(PluginError::UnknownPermission(other.to_string())),
        }
    }
}

/// A fine-grained permission a plugin must be granted to access a resource.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Permission {
    /// Read access to the telemetry store.
    ReadTelemetry,
    /// Write access to actuators / device commands.
    WriteDevice,
    /// Read access to the knowledge graph.
    ReadKnowledge,
    /// Write access to the knowledge graph.
    WriteKnowledge,
    /// Network egress (HTTP/WebSocket) to external endpoints.
    NetworkEgress,
    /// Spawn and manage child processes.
    SpawnProcess,
    /// Access to local filesystem paths outside the plugin sandbox.
    FilesystemAccess,
}

impl std::fmt::Display for Permission {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl Permission {
    pub fn as_str(&self) -> &'static str {
        match self {
            Permission::ReadTelemetry => "read_telemetry",
            Permission::WriteDevice => "write_device",
            Permission::ReadKnowledge => "read_knowledge",
            Permission::WriteKnowledge => "write_knowledge",
            Permission::NetworkEgress => "network_egress",
            Permission::SpawnProcess => "spawn_process",
            Permission::FilesystemAccess => "filesystem_access",
        }
    }

    /// Parses a permission from its snake_case string form.
    pub fn parse(s: &str) -> Result<Permission, PluginError> {
        match s {
            "read_telemetry" => Ok(Permission::ReadTelemetry),
            "write_device" => Ok(Permission::WriteDevice),
            "read_knowledge" => Ok(Permission::ReadKnowledge),
            "write_knowledge" => Ok(Permission::WriteKnowledge),
            "network_egress" => Ok(Permission::NetworkEgress),
            "spawn_process" => Ok(Permission::SpawnProcess),
            "filesystem_access" => Ok(Permission::FilesystemAccess),
            other => Err(PluginError::UnknownPermission(other.to_string())),
        }
    }
}

/// The plugin's declared manifest. This is the on-disk `plugin.json` contract.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PluginManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: String,
    pub capabilities: Vec<Capability>,
    pub permissions: Vec<Permission>,
    pub entrypoint: String,
}

impl PluginManifest {
    pub fn from_json(s: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(s)
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }

    /// Checks that every requested permission corresponds to a declared
    /// capability (a plugin may not request access it does not advertise).
    pub fn validate(&self) -> Result<(), PluginError> {
        let mut granted: HashSet<Permission> = self.permissions.iter().copied().collect();
        for cap in &self.capabilities {
            for required in required_permissions(*cap) {
                granted.insert(*required);
            }
        }
        // Every permission must be reachable from a capability.
        for perm in &self.permissions {
            let justified = self
                .capabilities
                .iter()
                .any(|c| required_permissions(*c).contains(perm));
            if !justified {
                return Err(PluginError::PermissionDenied(*perm));
            }
        }
        Ok(())
    }

    /// Returns whether the manifest requests the given permission.
    pub fn grants(&self, perm: Permission) -> bool {
        self.permissions.contains(&perm)
    }
}

/// The set of permissions implicitly required by a capability.
fn required_permissions(cap: Capability) -> &'static [Permission] {
    match cap {
        Capability::TelemetryRead => &[Permission::ReadTelemetry],
        Capability::DeviceControl => &[Permission::WriteDevice],
        Capability::AnalysisTool => &[Permission::ReadKnowledge],
        Capability::Optimization => &[Permission::ReadKnowledge],
        Capability::UiExtension => &[],
        Capability::AutonomousLoop => &[Permission::SpawnProcess],
    }
}

/// Health status reported by a plugin.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Health {
    Healthy,
    Degraded,
    Unhealthy,
}

/// A plugin lifecycle context carrying the permissions the host granted.
#[derive(Debug, Clone, Default)]
pub struct PluginContext {
    pub granted_permissions: HashSet<Permission>,
}

impl PluginContext {
    /// Asserts that the context grants `perm`, returning an error otherwise.
    pub fn require(&self, perm: Permission) -> Result<(), PluginError> {
        if self.granted_permissions.contains(&perm) {
            Ok(())
        } else {
            Err(PluginError::PermissionDenied(perm))
        }
    }
}

/// The plugin lifecycle contract every Prometheus plugin implements.
///
/// Implementations are expected to be `Send + Sync` so they can be shared
/// across the async runtime.
pub trait BasePlugin: Send + Sync {
    /// Returns the plugin's manifest.
    fn manifest(&self) -> &PluginManifest;

    /// Initializes the plugin against the provided host context.
    fn initialize(&mut self, ctx: &PluginContext) -> Result<(), PluginError>;

    /// Executes the named action with the supplied JSON payload.
    fn execute(&self, action: &str, payload: &serde_json::Value) -> Result<serde_json::Value, PluginError>;

    /// Gracefully shuts the plugin down.
    fn shutdown(&mut self) -> Result<(), PluginError>;

    /// Reports the plugin's current health.
    fn health(&self) -> Health;
}

/// A minimal in-memory plugin used for testing and as a reference example.
#[derive(Debug)]
pub struct EchoPlugin {
    manifest: PluginManifest,
    initialized: bool,
    healthy: Health,
}

impl EchoPlugin {
    pub fn new(manifest: PluginManifest) -> Self {
        Self {
            manifest,
            initialized: false,
            healthy: Health::Healthy,
        }
    }
}

impl BasePlugin for EchoPlugin {
    fn manifest(&self) -> &PluginManifest {
        &self.manifest
    }

    fn initialize(&mut self, _ctx: &PluginContext) -> Result<(), PluginError> {
        if self.initialized {
            return Err(PluginError::AlreadyInitialized(self.manifest.id.clone()));
        }
        self.initialized = true;
        tracing::info!(plugin = %self.manifest.id, "echo plugin initialized");
        Ok(())
    }

    fn execute(&self, action: &str, payload: &serde_json::Value) -> Result<serde_json::Value, PluginError> {
        if !self.initialized {
            return Err(PluginError::NotInitialized(self.manifest.id.clone()));
        }
        tracing::debug!(plugin = %self.manifest.id, %action, "executing action");
        Ok(serde_json::json!({ "action": action, "echo": payload }))
    }

    fn shutdown(&mut self) -> Result<(), PluginError> {
        self.initialized = false;
        Ok(())
    }

    fn health(&self) -> Health {
        self.healthy
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_manifest() -> PluginManifest {
        PluginManifest {
            id: "plg-echo".into(),
            name: "Echo Plugin".into(),
            version: "1.0.0".into(),
            description: "Echoes payloads back".into(),
            author: "prometheus".into(),
            capabilities: vec![Capability::AnalysisTool],
            permissions: vec![Permission::ReadKnowledge],
            entrypoint: "libecho.so".into(),
        }
    }

    #[test]
    fn capability_parse_roundtrip() {
        assert_eq!(Capability::parse("device-control").unwrap(), Capability::DeviceControl);
        assert_eq!(Capability::DeviceControl.as_str(), "device-control");
        assert!(Capability::parse("nonsense").is_err());
    }

    #[test]
    fn permission_parse_roundtrip() {
        assert_eq!(Permission::parse("read_telemetry").unwrap(), Permission::ReadTelemetry);
        assert_eq!(Permission::ReadTelemetry.as_str(), "read_telemetry");
        assert!(Permission::parse("evil").is_err());
    }

    #[test]
    fn manifest_json_roundtrip() {
        let m = sample_manifest();
        let json = m.to_json().unwrap();
        let back = PluginManifest::from_json(&json).unwrap();
        assert_eq!(back, m);
    }

    #[test]
    fn manifest_validates_justified_permissions() {
        assert!(sample_manifest().validate().is_ok());
    }

    #[test]
    fn manifest_rejects_unjustified_permission() {
        let mut m = sample_manifest();
        m.permissions.push(Permission::NetworkEgress);
        assert!(matches!(m.validate(), Err(PluginError::PermissionDenied(Permission::NetworkEgress))));
    }

    #[test]
    fn echo_plugin_lifecycle() {
        let mut p = EchoPlugin::new(sample_manifest());
        assert_eq!(p.health(), Health::Healthy);
        assert!(p.execute("ping", &serde_json::json!({})).is_err());
        p.initialize(&PluginContext::default()).unwrap();
        let out = p.execute("ping", &serde_json::json!({"x": 1})).unwrap();
        assert_eq!(out["action"], "ping");
        assert_eq!(out["echo"]["x"], 1);
        p.shutdown().unwrap();
        assert!(p.execute("ping", &serde_json::json!({})).is_err());
    }

    #[test]
    fn double_initialize_errors() {
        let mut p = EchoPlugin::new(sample_manifest());
        p.initialize(&PluginContext::default()).unwrap();
        assert!(matches!(
            p.initialize(&PluginContext::default()),
            Err(PluginError::AlreadyInitialized(_))
        ));
    }

    #[test]
    fn context_require_permission() {
        let mut ctx = PluginContext::default();
        ctx.granted_permissions.insert(Permission::ReadKnowledge);
        assert!(ctx.require(Permission::ReadKnowledge).is_ok());
        assert!(matches!(
            ctx.require(Permission::WriteDevice),
            Err(PluginError::PermissionDenied(Permission::WriteDevice))
        ));
    }
}
