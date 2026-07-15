//! P3 Aether AI Runtime — provider abstraction, routing, tool dispatch,
//! and a short/long memory context engine (Rust FFI boundary).
//!
//! The Python `aether` package calls into this crate via PyO3; if the
//! compiled extension is unavailable it falls back to a pure-Python
//! runtime (see `aether/runtime.py`).

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AetherError {
    #[error("no provider available")]
    NoProvider,
    #[error("unknown tool: {0}")]
    UnknownTool(String),
    #[error("tool '{0}' failed: {1}")]
    ToolFailed(String, String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderInfo {
    pub name: String,
    pub model: String,
    pub cost_per_1k: f64,
    pub latency_score: f64,
    pub available: bool,
}

impl ProviderInfo {
    pub fn new(name: &str, model: &str, cost_per_1k: f64, latency_score: f64) -> Self {
        Self {
            name: name.into(),
            model: model.into(),
            cost_per_1k,
            latency_score,
            available: true,
        }
    }
}

/// Default local-first provider catalog.
pub fn default_providers() -> Vec<ProviderInfo> {
    vec![
        ProviderInfo::new("ollama", "local-model", 0.0, 1.0),
        ProviderInfo::new("openai", "gpt-4o-mini", 0.15, 2.0),
        ProviderInfo::new("anthropic", "claude-haiku", 0.25, 2.5),
    ]
}

/// Cost/perf-aware router with a fallback chain.
pub struct Router {
    providers: Vec<ProviderInfo>,
    budget_cap: f64,
}

impl Router {
    pub fn new(providers: Vec<ProviderInfo>, budget_cap: f64) -> Self {
        Self { providers, budget_cap }
    }

    pub fn route(&self, budget: Option<f64>) -> Result<ProviderInfo, AetherError> {
        let cap = budget.unwrap_or(self.budget_cap);
        let available: Vec<ProviderInfo> = self.providers.iter().filter(|p| p.available).cloned().collect();
        if available.is_empty() {
            return Err(AetherError::NoProvider);
        }
        let mut pool: Vec<ProviderInfo> = available.iter().filter(|p| p.cost_per_1k <= cap).cloned().collect();
        if pool.is_empty() {
            pool = available;
        }
        pool.sort_by(|a, b| {
            a.cost_per_1k
                .partial_cmp(&b.cost_per_1k)
                .unwrap()
                .then(a.latency_score.partial_cmp(&b.latency_score).unwrap())
        });
        Ok(pool[0].clone())
    }

    pub fn fallback_chain(&self, preferred: &ProviderInfo) -> Vec<ProviderInfo> {
        self.providers
            .iter()
            .filter(|p| p.available && p.name != preferred.name)
            .cloned()
            .collect()
    }
}

/// Tool dispatcher: capability calls isolated per tool.
pub struct ToolDispatcher {
    handlers: std::collections::HashMap<String, Box<dyn Fn(serde_json::Value) -> Result<serde_json::Value, String> + Send + Sync>>,
}

impl ToolDispatcher {
    pub fn new() -> Self {
        Self { handlers: std::collections::HashMap::new() }
    }

    pub fn register<F>(&mut self, tool: &str, handler: F)
    where
        F: Fn(serde_json::Value) -> Result<serde_json::Value, String> + Send + Sync + 'static,
    {
        self.handlers.insert(tool.into(), Box::new(handler));
    }

    pub fn dispatch(&self, tool: &str, args: serde_json::Value) -> Result<serde_json::Value, AetherError> {
        let handler = self.handlers.get(tool).ok_or_else(|| AetherError::UnknownTool(tool.into()))?;
        handler(args).map_err(|e| AetherError::ToolFailed(tool.into(), e))
    }
}

/// Short/long memory context engine.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ContextStore {
    pub short_term: Vec<String>,
    pub long_term: Vec<String>,
}

impl ContextStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push_short(&mut self, msg: &str) {
        self.short_term.push(msg.into());
    }

    pub fn archive(&mut self) {
        self.long_term.extend(self.short_term.drain(..));
    }

    pub fn snapshot(&self) -> serde_json::Value {
        serde_json::json!({
            "short_term": self.short_term,
            "long_term": self.long_term,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn router_prefers_cheapest_within_budget() {
        let r = Router::new(default_providers(), 1.0);
        let sel = r.route(None).unwrap();
        assert_eq!(sel.name, "ollama");
    }

    #[test]
    fn router_over_budget_picks_lowest_latency() {
        let r = Router::new(
            vec![
                ProviderInfo::new("openai", "gpt-4o-mini", 0.15, 2.0),
                ProviderInfo::new("ollama", "local-model", 0.0, 1.0),
            ],
            0.0,
        );
        let sel = r.route(None).unwrap();
        assert_eq!(sel.name, "ollama");
    }

    #[test]
    fn fallback_excludes_preferred() {
        let r = Router::new(default_providers(), 1.0);
        let preferred = r.route(None).unwrap();
        let chain = r.fallback_chain(&preferred);
        assert!(!chain.iter().any(|p| p.name == preferred.name));
    }

    #[test]
    fn tool_dispatch_isolated() {
        let mut d = ToolDispatcher::new();
        d.register("ping", |a| Ok(serde_json::json!({"pong": a["n"]})));
        d.register("boom", |_| Err("kaboom".into()));
        assert!(d.dispatch("ping", serde_json::json!({"n": 1})).is_ok());
        assert!(matches!(d.dispatch("boom", serde_json::Value::Null), Err(AetherError::ToolFailed(_, _))));
        assert!(matches!(d.dispatch("nope", serde_json::Value::Null), Err(AetherError::UnknownTool(_))));
    }

    #[test]
    fn context_engine_archives() {
        let mut ctx = ContextStore::new();
        ctx.push_short("hello");
        ctx.archive();
        assert!(ctx.short_term.is_empty());
        assert_eq!(ctx.long_term.len(), 1);
    }
}
