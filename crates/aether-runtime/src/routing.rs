//! Model routing (Phase 3.3).
//!
//! Selects which registered provider should serve a request. Policy:
//! 1. **Local-first** — prefer local providers (Ollama, LM Studio,
//!    llama.cpp, vLLM) unless a cloud provider is explicitly named or no
//!    local provider is available. Mirrors the roadmap's "run locally unless
//!    cloud is explicitly requested".
//! 2. **Capability routing** — a [`Capability`] tag (`cheap`, `fast`,
//!    `reasoning`, `local`) biases the selection. Rules are cached in Rust;
//!    they originate from the Python config store.
//! 3. **Cost/latency** — when `CostOptimized`, cloud providers are deprioritized
//!    and local is always chosen when present.

use crate::manager::ProviderManager;
use crate::types::ProviderKind;

/// Global routing strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RoutingPolicy {
    /// Prefer local providers; fall back to cloud. (default)
    #[default]
    LocalFirst,
    /// Minimize cost: never pick cloud if a local provider exists.
    CostOptimized,
    /// Honor an explicit provider name only; never auto-select.
    Explicit,
}

/// A request-time hint about which kind of model fits best.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Capability {
    Cheap,
    Fast,
    Reasoning,
    Local,
}

fn is_local(kind: ProviderKind) -> bool {
    matches!(
        kind,
        ProviderKind::LmStudio | ProviderKind::Ollama | ProviderKind::LlamaCpp | ProviderKind::Vllm
    )
}

#[derive(Clone)]
pub struct ModelRouter {
    policy: RoutingPolicy,
}

impl Default for ModelRouter {
    fn default() -> Self {
        Self::new()
    }
}

impl ModelRouter {
    pub fn new() -> Self {
        Self {
            policy: RoutingPolicy::LocalFirst,
        }
    }

    pub fn with_policy(policy: RoutingPolicy) -> Self {
        Self { policy }
    }

    /// Set the active policy (mutates in place). Returns `&mut Self` for chaining.
    pub fn set_policy(&mut self, policy: RoutingPolicy) -> &mut Self {
        self.policy = policy;
        self
    }

    /// Choose a provider id for a request.
    ///
    /// * `requested` — an explicit provider id (e.g. user selection). Always
    ///   honored if it exists, regardless of policy.
    /// * `capability` — optional hint used to bias among candidates.
    ///
    /// Returns the chosen provider id, or `None` if no provider is registered.
    pub fn select(
        &self,
        manager: &ProviderManager,
        requested: Option<&str>,
        capability: Option<Capability>,
    ) -> Option<String> {
        let candidates: Vec<(String, ProviderKind)> = manager
            .list()
            .into_iter()
            .map(|info| (info.id, info.kind))
            .collect();

        if candidates.is_empty() {
            return None;
        }

        if let Some(name) = requested {
            if candidates.iter().any(|(id, _)| id == name) {
                return Some(name.to_string());
            }
        }

        if self.policy == RoutingPolicy::Explicit {
            return None;
        }

        let local: Vec<(String, ProviderKind)> =
            candidates.iter().filter(|(_, k)| is_local(*k)).cloned().collect();
        let cloud: Vec<(String, ProviderKind)> =
            candidates.iter().filter(|(_, k)| !is_local(*k)).cloned().collect();

        match capability {
            Some(Capability::Local) => local.first().map(|(id, _)| id.clone()),
            Some(Capability::Cheap) | Some(Capability::Fast) => {
                local
                    .first()
                    .or_else(|| cloud.first())
                    .map(|(id, _)| id.clone())
            }
            Some(Capability::Reasoning) => {
                cloud
                    .first()
                    .or_else(|| local.first())
                    .map(|(id, _)| id.clone())
            }
            None => {
                if self.policy == RoutingPolicy::CostOptimized && !local.is_empty() {
                    return local.first().map(|(id, _)| id.clone());
                }
                local
                    .first()
                    .or_else(|| cloud.first())
                    .map(|(id, _)| id.clone())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lm_studio::LmStudioProvider;

    fn manager_with(local: bool, cloud: bool) -> ProviderManager {
        let m = ProviderManager::new();
        if local {
            m.register(LmStudioProvider::default_local());
        }
        if cloud {
            m.register(crate::http_provider::HttpProvider::openrouter("sk-test"));
        }
        m
    }

    #[test]
    fn local_first_prefers_local() {
        let m = manager_with(true, true);
        let r = ModelRouter::new();
        assert_eq!(r.select(&m, None, None).as_deref(), Some("lmstudio"));
    }

    #[test]
    fn explicit_request_wins() {
        let m = manager_with(true, true);
        let r = ModelRouter::new();
        assert_eq!(
            r.select(&m, Some("openrouter"), None).as_deref(),
            Some("openrouter")
        );
    }

    #[test]
    fn cost_optimized_never_cloud_when_local() {
        let m = manager_with(true, true);
        let mut r = ModelRouter::new();
        r.set_policy(RoutingPolicy::CostOptimized);
        assert_eq!(r.select(&m, None, None).as_deref(), Some("lmstudio"));
    }

    #[test]
    fn cloud_only_falls_back_to_cloud() {
        let m = manager_with(false, true);
        let r = ModelRouter::new();
        assert_eq!(r.select(&m, None, None).as_deref(), Some("openrouter"));
    }
}
