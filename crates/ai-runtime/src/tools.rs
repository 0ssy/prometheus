//! Tool dispatcher (Phase 3.5).
//!
//! Maps a tool name + arguments onto the Prometheus Python backend's HTTP
//! surface and returns a structured result of the shape
//! `{"ok": true, "data": ...}` or `{"ok": false, "error": "..."}`.
//!
//! **Approval gating (Stage 6 contract):** mutating tools never execute
//! unless the caller passes `approved = true`. Reads are always allowed. This
//! keeps the runtime fail-safe: an unapproved mutating call returns an error
//! rather than silently performing an action.

use crate::error::AetherError;
use reqwest::Client;
use serde_json::{json, Value};

/// Where a tool is dispatched on the backend.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ToolTarget {
    /// `POST /capabilities/execute` (HAL + generic capability surface).
    Capability,
    /// A dedicated endpoint path (relative to the backend base URL).
    Endpoint(&'static str),
}

/// A tool the runtime can invoke against the backend.
#[derive(Clone, Copy, Debug)]
pub struct Tool {
    pub name: &'static str,
    pub description: &'static str,
    /// Whether executing the tool changes state (requires approval).
    pub mutating: bool,
    pub target: ToolTarget,
}

/// Canonical tool registry (Phase 3.5 map). Mirrors the roadmap's
/// tool → endpoint table.
pub fn registry() -> &'static [Tool] {
    &[
        Tool { name: "filesystem", description: "Read/write local files", mutating: true, target: ToolTarget::Endpoint("/fs/execute") },
        Tool { name: "terminal", description: "Execute a shell command", mutating: true, target: ToolTarget::Endpoint("/terminal/execute") },
        Tool { name: "git", description: "Git status/diff/commit", mutating: true, target: ToolTarget::Endpoint("/git/execute") },
        Tool { name: "hardware", description: "HAL capabilities (connect/read/write/diagnose/flash)", mutating: true, target: ToolTarget::Capability },
        Tool { name: "browser", description: "Open URLs / capture screenshots", mutating: false, target: ToolTarget::Endpoint("/browser/execute") },
        Tool { name: "sdk", description: "Run plugins / dispatch agents", mutating: true, target: ToolTarget::Endpoint("/plugins/execute") },
        Tool { name: "apis", description: "Generic capability execution", mutating: true, target: ToolTarget::Capability },
        Tool { name: "knowledge_graph", description: "Query the knowledge graph", mutating: false, target: ToolTarget::Endpoint("/knowledge/execute") },
        Tool { name: "engineering", description: "Execute engineering workflows (embedded, robotics, mechanical, electrical, networking, cybersecurity, ai, data, cloud)", mutating: true, target: ToolTarget::Endpoint("/engineering/execute") },
    ]
}

/// Resolve a tool by name.
pub fn lookup(name: &str) -> Option<&'static Tool> {
    registry().iter().find(|t| t.name == name)
}

/// Dispatches tool calls to the Prometheus backend (Phase 3.5).
#[derive(Clone)]
pub struct ToolDispatcher {
    backend_url: String,
    client: Client,
}

impl Default for ToolDispatcher {
    fn default() -> Self {
        Self::new()
    }
}

impl ToolDispatcher {
    pub fn new() -> Self {
        Self {
            backend_url: crate::DEFAULT_BACKEND_URL.to_string(),
            client: Client::new(),
        }
    }

    /// Point the dispatcher at a specific backend (e.g. the test sidecar).
    pub fn with_backend(backend_url: impl Into<String>) -> Self {
        Self {
            backend_url: backend_url.into(),
            client: Client::new(),
        }
    }

    /// Dispatch `tool` with `args`. `approved` must be true for mutating
    /// tools. Returns the backend's structured payload on success.
    pub async fn dispatch(
        &self,
        tool: &str,
        args: Value,
        approved: bool,
    ) -> Result<Value, AetherError> {
        let tool = lookup(tool).ok_or_else(|| {
            AetherError::Provider(format!("unknown tool: {tool}"))
        })?;

        if tool.mutating && !approved {
            return Err(AetherError::Provider(format!(
                "tool '{}' is mutating and requires explicit approval",
                tool.name
            )));
        }

        let (path, body) = match tool.target {
            ToolTarget::Capability => (
                "/capabilities/execute",
                json!({
                    "name": args.get("capability").cloned().unwrap_or(Value::Null),
                    "payload": args.get("payload").cloned().unwrap_or(Value::Object(Default::default())),
                    "granted_permissions": args.get("granted_permissions").cloned().unwrap_or(Value::Array(vec![])),
                }),
            ),
            ToolTarget::Endpoint(p) => (
                p,
                json!({ "tool": tool.name, "args": args }),
            ),
        };

        let url = format!("{}{}", self.backend_url.trim_end_matches('/'), path);
        let resp = self.client.post(&url).json(&body).send().await?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            return Err(AetherError::Provider(format!(
                "tool '{0}' backend error ({1}): {2}",
                tool.name, status, text
            )));
        }

        let value: Value = resp.json().await?;
        // Normalize: if the backend already returns {ok, data/error}, pass it
        // through; otherwise wrap the body as {ok: true, data: value}.
        if value.get("ok").is_some() {
            Ok(value)
        } else {
            Ok(json!({ "ok": true, "data": value }))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use httpmock::prelude::*;

    #[test]
    fn unknown_tool_errors() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let d = ToolDispatcher::new();
            let err = d.dispatch("nope", json!({}), false).await.unwrap_err();
            assert!(err.to_string().contains("unknown tool"));
        });
    }

    #[test]
    fn mutating_requires_approval() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let d = ToolDispatcher::new();
            let err = d
                .dispatch("terminal", json!({"command": "rm -rf /"}), false)
                .await
                .unwrap_err();
            assert!(err.to_string().contains("requires explicit approval"));
        });
    }

    #[tokio::test]
    async fn read_tool_dispatches_without_approval() {
        let server = MockServer::start();
        let ep = server.mock(|when, then| {
            when.method(POST).path("/knowledge/execute");
            then.status(200).json_body(json!({"ok": true, "data": {"facts": 3}}));
        });
        let d = ToolDispatcher::with_backend(server.base_url());
        let res = d
            .dispatch("knowledge_graph", json!({"query": "x"}), false)
            .await
            .unwrap();
        assert_eq!(res["ok"], true);
        assert_eq!(res["data"]["facts"], 3);
        ep.assert();
    }

    #[tokio::test]
    async fn mutating_dispatches_when_approved() {
        let server = MockServer::start();
        let ep = server.mock(|when, then| {
            when.method(POST).path("/capabilities/execute");
            then.status(200).json_body(json!({"ok": true, "data": {"flashed": true}}));
        });
        let d = ToolDispatcher::with_backend(server.base_url());
        let res = d
            .dispatch(
                "hardware",
                json!({"capability": "hardware.flash", "payload": {"device": "x"}}),
                true,
            )
            .await
            .unwrap();
        assert_eq!(res["ok"], true);
        ep.assert();
    }

    #[tokio::test]
    async fn engineering_tool_dispatches() {
        let server = MockServer::start();
        let ep = server.mock(|when, then| {
            when.method(POST).path("/engineering/execute");
            then.status(200).json_body(json!({"ok": true, "data": {"module": "networking", "packets": 42}}));
        });
        let d = ToolDispatcher::with_backend(server.base_url());
        let res = d
            .dispatch(
                "engineering",
                json!({"module_name": "networking", "workflow": "capture_packets", "payload": {"interface": "eth0"}}),
                true,
            )
            .await
            .unwrap();
        assert_eq!(res["ok"], true);
        assert_eq!(res["data"]["packets"], 42);
        ep.assert();
    }
}
