//! Tool dispatcher — reserved for Stage 5. Stubbed in Milestone 1.

use crate::error::AetherError;

/// Routes a tool call to the appropriate backend capability.
///
/// Stage 5 contract: map `name` + `args` onto the existing Prometheus
/// capability surface (`POST /capabilities/execute`, plus device/plugin
/// endpoints) via `PlatformService.execute_capability`. Stage 6 will gate
/// mutating tools behind explicit user approval. In M1 all dispatches error
/// out so the command surface fails safe rather than inventing an HTTP path.
#[derive(Clone, Default)]
pub struct ToolDispatcher;

impl ToolDispatcher {
    pub fn new() -> Self {
        Self
    }

    /// Dispatch a tool call. Always returns `Err` in M1.
    pub async fn dispatch(
        &self,
        name: &str,
        args: serde_json::Value,
    ) -> Result<serde_json::Value, AetherError> {
        let _ = (name, args);
        Err(AetherError::Provider(
            "tool calling not implemented in M1".to_string(),
        ))
    }
}
