//! Provider manager: orchestrates the registry, defaults, and bulk health.

use std::sync::Mutex;

use crate::error::AetherError;
use crate::provider::Provider;
use crate::registry::ProviderRegistry;
use crate::types::{CostAccumulator, ProviderHealth, ProviderInfo, ProviderKind};

/// Wraps the [`ProviderRegistry`] with default selection and bulk operations.
///
/// Cheap to clone (`Arc`/`Mutex` interior); the Tauri runtime stores one copy
/// per state slot. Narrow lock scope: only the registry/handle fields are
/// guarded here, so chat calls do not contend on the manager mutex.
pub struct ProviderManager {
    registry: ProviderRegistry,
    default_id: Mutex<Option<String>>,
    costs: Mutex<CostAccumulator>,
}

impl Clone for ProviderManager {
    fn clone(&self) -> Self {
        Self {
            registry: self.registry.clone(),
            default_id: Mutex::new(
                self.default_id
                    .lock()
                    .expect("default lock poisoned")
                    .clone(),
            ),
            costs: Mutex::new(
                self.costs
                    .lock()
                    .expect("costs lock poisoned")
                    .clone(),
            ),
        }
    }
}

impl Default for ProviderManager {
    fn default() -> Self {
        Self::new()
    }
}

impl ProviderManager {
    pub fn new() -> Self {
        Self {
            registry: ProviderRegistry::new(),
            default_id: Mutex::new(None),
            costs: Mutex::new(CostAccumulator::default()),
        }
    }

    /// Register a provider. If no default is set yet, the first registered
    /// provider becomes the default automatically.
    pub fn register(&self, provider: std::sync::Arc<dyn Provider>) {
        let is_first = self.registry.is_empty();
        let id = provider.id().to_string();
        self.registry.register(provider);
        if is_first {
            *self.default_id.lock().expect("default lock poisoned") = Some(id);
        }
    }

    /// Remove a provider. If it was the default, the default falls back to the
    /// first remaining provider (or `None` if the registry is now empty).
    pub fn unregister(&self, id: &str) -> bool {
        let removed = self.registry.unregister(id);
        if removed {
            let mut default = self.default_id.lock().expect("default lock poisoned");
            if default.as_deref() == Some(id) {
                *default = self.registry.ids().into_iter().next();
            }
        }
        removed
    }

    /// Borrow a provider by id.
    pub fn get(&self, id: &str) -> Option<std::sync::Arc<dyn Provider>> {
        self.registry.get(id)
    }

    /// List all providers as lightweight [`ProviderInfo`] records.
    pub fn list(&self) -> Vec<ProviderInfo> {
        let default = self
            .default_id
            .lock()
            .expect("default lock poisoned")
            .clone();
        self.registry
            .all()
            .iter()
            .map(|p| ProviderInfo {
                id: p.id().to_string(),
                kind: p.kind(),
                name: p.name().to_string(),
                default: default.as_deref() == Some(p.id()),
            })
            .collect()
    }

    /// The current default provider id (explicit, else first registered).
    pub fn default_id(&self) -> Option<String> {
        self.default_id
            .lock()
            .expect("default lock poisoned")
            .clone()
            .or_else(|| self.registry.ids().into_iter().next())
    }

    /// Set the default provider by id. Returns an error if unknown.
    pub fn set_default(&self, id: &str) -> Result<(), AetherError> {
        if self.registry.get(id).is_none() {
            return Err(AetherError::NotFound(id.to_string()));
        }
        *self.default_id.lock().expect("default lock poisoned") = Some(id.to_string());
        Ok(())
    }

    /// Resolve the provider to use for a request: the named one if provided,
    /// else the default.
    pub fn resolve(&self, name: Option<&str>) -> Result<std::sync::Arc<dyn Provider>, AetherError> {
        match name {
            Some(id) => self
                .registry
                .get(id)
                .ok_or_else(|| AetherError::NotFound(id.to_string())),
            None => {
                let id = self
                    .default_id()
                    .ok_or_else(|| AetherError::Provider("no provider available".to_string()))?;
                self.registry
                    .get(&id)
                    .ok_or_else(|| AetherError::NotFound(id))
            }
        }
    }

    /// Run a chat completion against the resolved provider.
    pub async fn chat(
        &self,
        name: Option<&str>,
        req: crate::types::ChatRequest,
    ) -> Result<crate::types::ChatResponse, AetherError> {
        let provider = self.resolve(name)?;
        provider.chat(req).await
    }

    /// Probe every registered provider concurrently and collect their health.
    pub async fn health_all(&self) -> Vec<(String, ProviderHealth)> {
        let handles: Vec<_> = self
            .registry
            .all()
            .iter()
            .map(|p| {
                let id = p.id().to_string();
                let provider = p.clone();
                async move { (id, provider.health().await) }
            })
            .collect();

        let mut results = Vec::with_capacity(handles.len());
        for h in handles {
            results.push(h.await);
        }
        results
    }

    /// Convenience: the kind of the default provider (if any).
    pub fn default_kind(&self) -> Option<ProviderKind> {
        self.default_id()
            .and_then(|id| self.registry.get(&id).map(|p| p.kind()))
    }

    /// Record token usage and estimated cost for a completed request.
    pub fn record_cost(&self, provider_id: &str, prompt_tokens: u64, completion_tokens: u64) {
        let cost = self.registry.get(provider_id).map(|p| p.cost_per_1k()).unwrap_or(0.0);
        let mut costs = self.costs.lock().expect("costs lock poisoned");
        costs.record(prompt_tokens, completion_tokens, cost);
    }

    /// Snapshot of accumulated costs across all providers.
    pub fn costs(&self) -> CostAccumulator {
        self.costs.lock().expect("costs lock poisoned").clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{ChatRequest, ChatResponse, ProviderHealth};
    use async_trait::async_trait;
    use std::sync::Arc;

    struct MockProvider {
        id: String,
        name: String,
        healthy: bool,
    }

    #[async_trait]
    impl Provider for MockProvider {
        fn id(&self) -> &str {
            &self.id
        }
        fn kind(&self) -> ProviderKind {
            ProviderKind::CustomHttp
        }
        fn name(&self) -> &str {
            &self.name
        }
        async fn health(&self) -> ProviderHealth {
            if self.healthy {
                ProviderHealth::ok(1)
            } else {
                ProviderHealth::err("mock down")
            }
        }
        async fn chat(&self, req: ChatRequest) -> Result<ChatResponse, AetherError> {
            Ok(ChatResponse {
                content: format!(
                    "echo:{}",
                    req.messages
                        .last()
                        .map(|m| m.content.clone())
                        .unwrap_or_default()
                ),
                tool_calls: None,
                model: req.model,
            })
        }
        async fn list_models(&self) -> Result<Vec<String>, AetherError> {
            Ok(vec!["mock-model".to_string()])
        }
    }

    fn mock(id: &str, healthy: bool) -> Arc<dyn Provider> {
        Arc::new(MockProvider {
            id: id.to_string(),
            name: id.to_uppercase(),
            healthy,
        })
    }

    #[test]
    fn first_registered_becomes_default() {
        let m = ProviderManager::new();
        assert!(m.default_id().is_none());
        m.register(mock("a", true));
        assert_eq!(m.default_id().as_deref(), Some("a"));
        m.register(mock("b", true));
        assert_eq!(m.default_id().as_deref(), Some("a"));
    }

    #[test]
    fn set_default_unknown_errors() {
        let m = ProviderManager::new();
        m.register(mock("a", true));
        assert!(m.set_default("missing").is_err());
        assert!(m.set_default("a").is_ok());
    }

    #[test]
    fn unregister_default_falls_back() {
        let m = ProviderManager::new();
        m.register(mock("a", true));
        m.register(mock("b", true));
        assert!(m.unregister("a"));
        assert_eq!(m.default_id().as_deref(), Some("b"));
        assert!(m.unregister("b"));
        assert!(m.default_id().is_none());
    }

    #[tokio::test]
    async fn health_all_preserves_order() {
        let m = ProviderManager::new();
        m.register(mock("first", true));
        m.register(mock("second", false));
        let health = m.health_all().await;
        assert_eq!(
            health.iter().map(|(id, _)| id.as_str()).collect::<Vec<_>>(),
            vec!["first", "second"]
        );
        assert!(health[0].1.ok);
        assert!(!health[1].1.ok);
    }

    #[tokio::test]
    async fn chat_uses_default_when_unnamed() {
        let m = ProviderManager::new();
        m.register(mock("a", true));
        let resp = m
            .chat(None, ChatRequest::from_prompt("m", "hi"))
            .await
            .unwrap();
        assert_eq!(resp.content, "echo:hi");
    }

    #[tokio::test]
    async fn chat_errors_when_no_provider() {
        let m = ProviderManager::new();
        let err = m
            .chat(None, ChatRequest::from_prompt("m", "hi"))
            .await
            .unwrap_err();
        assert!(matches!(err, AetherError::Provider(_)));
    }
}
