//! Context engine (Phase3.2).
//!
//! Assembles a [`Context`] packet for the next model turn by pulling from the
//! Prometheus backend's REST surface (`/knowledge`, `/memory`, `/devices`,
//! `/agents`) and the workspace. Network failures degrade gracefully — a
//! section simply stays empty rather than failing the whole turn.

use serde::{Deserialize, Serialize};

use crate::DEFAULT_BACKEND_URL;

/// A context packet assembled from workspace/project/knowledge/memory/hardware/
/// agents/terminal sources.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Context {
    #[serde(default)]
    pub workspace: Vec<String>,
    #[serde(default)]
    pub project: Vec<String>,
    #[serde(default)]
    pub files: Vec<String>,
    #[serde(default)]
    pub knowledge: Vec<String>,
    #[serde(default)]
    pub memory: Vec<String>,
    #[serde(default)]
    pub hardware: Vec<String>,
    #[serde(default)]
    pub agents: Vec<String>,
    #[serde(default)]
    pub terminal: Vec<String>,
}

impl Context {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn is_empty(&self) -> bool {
        self.workspace.is_empty()
            && self.project.is_empty()
            && self.files.is_empty()
            && self.knowledge.is_empty()
            && self.memory.is_empty()
            && self.hardware.is_empty()
            && self.agents.is_empty()
            && self.terminal.is_empty()
    }

    /// Total number of context items across all sections.
    pub fn len(&self) -> usize {
        self.workspace.len()
            + self.project.len()
            + self.files.len()
            + self.knowledge.len()
            + self.memory.len()
            + self.hardware.len()
            + self.agents.len()
            + self.terminal.len()
    }

    pub fn is_not_empty(&self) -> bool {
        !self.is_empty()
    }
}

/// Endpoint → context section mapping the engine queries.
struct Source {
    path: &'static str,
    field: &'static str,
}

const SOURCES: &[Source] = &[
    Source { path: "/knowledge/context", field: "knowledge" },
    Source { path: "/memory/context", field: "memory" },
    Source { path: "/devices/context", field: "hardware" },
    Source { path: "/agents/context", field: "agents" },
];

/// Assembles a [`Context`] for the next model turn.
#[derive(Clone)]
pub struct ContextEngine {
    backend_url: String,
    client: reqwest::Client,
    /// Max items kept per section after fetching.
    max_per_section: usize,
}

impl Default for ContextEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl ContextEngine {
    pub fn new() -> Self {
        Self {
            backend_url: DEFAULT_BACKEND_URL.to_string(),
            client: reqwest::Client::new(),
            max_per_section: 20,
        }
    }

    pub fn with_backend(backend_url: impl Into<String>) -> Self {
        Self {
            backend_url: backend_url.into(),
            client: reqwest::Client::new(),
            max_per_section: 20,
        }
    }

    /// Set the per-section item cap (for model-window trimming).
    pub fn with_limit(mut self, limit: usize) -> Self {
        self.max_per_section = limit;
        self
    }

    /// Build a full context packet across all sources.
    pub async fn assemble(&self) -> Context {
        let mut ctx = Context::empty();
        for source in SOURCES {
            if let Some(items) = self.fetch_list(source.path).await {
                let trimmed: Vec<String> = items.into_iter().take(self.max_per_section).collect();
                match source.field {
                    "knowledge" => ctx.knowledge = trimmed,
                    "memory" => ctx.memory = trimmed,
                    "hardware" => ctx.hardware = trimmed,
                    "agents" => ctx.agents = trimmed,
                    _ => {}
                }
            }
        }
        ctx
    }

    /// Fetch one context section by path. Returns `None` on any transport or
    /// shape error — the caller leaves that section empty.
    async fn fetch_list(&self, path: &str) -> Option<Vec<String>> {
        let url = format!("{}{}", self.backend_url.trim_end_matches('/'), path);
        let resp = self.client.get(&url).send().await.ok()?;
        if !resp.status().is_success() {
            return None;
        }
        let value: serde_json::Value = resp.json().await.ok()?;
        // Accept either {"items": [...]} or a bare array.
        let arr = value
            .get("items")
            .and_then(|i| i.as_array())
            .or_else(|| value.as_array())
            .cloned()?;
        Some(
            arr.into_iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use httpmock::prelude::*;
    use serde_json::json;

    #[tokio::test]
    async fn assemble_pulls_knowledge_and_hardware() {
        let server = MockServer::start();
        server.mock(|when, then| {
            when.method(GET).path("/knowledge/context");
            then.status(200).json_body(json!({"items": ["fact a", "fact b"]}));
        });
        server.mock(|when, then| {
            when.method(GET).path("/memory/context");
            then.status(200).json_body(json!({"items": []}));
        });
        server.mock(|when, then| {
            when.method(GET).path("/devices/context");
            then.status(200).json_body(json!({"items": ["device x"]}));
        });
        server.mock(|when, then| {
            when.method(GET).path("/agents/context");
            then.status(200).json_body(json!({"items": ["planner"]}));
        });

        let engine = ContextEngine::with_backend(server.base_url());
        let ctx = engine.assemble().await;
        assert_eq!(ctx.knowledge, vec!["fact a".to_string(), "fact b".to_string()]);
        assert_eq!(ctx.hardware, vec!["device x".to_string()]);
        assert_eq!(ctx.agents, vec!["planner".to_string()]);
        assert!(ctx.memory.is_empty());
        assert!(ctx.is_not_empty());
    }

    #[tokio::test]
    async fn assemble_degrades_when_backend_down() {
        // Base URL points nowhere reachable.
        let engine = ContextEngine::with_backend("http://127.0.0.1:1");
        let ctx = engine.assemble().await;
        assert!(ctx.is_empty());
    }
}
