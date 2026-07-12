//! Project Aether — Rust AI Runtime (Milestone 1).
//!
//! Abstraction layer over AI providers, intended to live *alongside* the
//! Python Prometheus platform. This milestone delivers the provider model, an
//! in-memory manager/registry, a backend-aware health checker, and a single
//! local provider (LM Studio). The context engine and tool dispatcher are
//! stubbed; later stages (4/5) populate them via the existing REST surface.

pub mod context;
pub mod error;
pub mod health;
pub mod lm_studio;
pub mod manager;
pub mod provider;
pub mod registry;
pub mod tools;
pub mod types;

pub use context::{Context, ContextEngine};
pub use error::AetherError;
pub use health::check_runtime;
pub use manager::ProviderManager;
pub use provider::Provider;
pub use registry::ProviderRegistry;
pub use tools::ToolDispatcher;
pub use types::{
    ChatMessage, ChatRequest, ChatResponse, ChatRole, ProviderHealth, ProviderInfo, ProviderKind,
    RuntimeHealth,
};

/// Default Prometheus backend address the sidecar listens on.
pub const DEFAULT_BACKEND_URL: &str = "http://127.0.0.1:8000";

/// Runtime bundle shared with the Tauri command surface: provider manager plus
/// the (stubbed) context engine and tool dispatcher.
#[derive(Clone)]
pub struct AetherRuntime {
    pub manager: ProviderManager,
    pub context: ContextEngine,
    pub tools: ToolDispatcher,
}

impl Default for AetherRuntime {
    fn default() -> Self {
        Self::new()
    }
}

impl AetherRuntime {
    /// Build a runtime and register the default local LM Studio provider.
    pub fn new() -> Self {
        let manager = ProviderManager::new();
        manager.register(lm_studio::LmStudioProvider::default_local());
        Self {
            manager,
            context: ContextEngine::new(),
            tools: ToolDispatcher::new(),
        }
    }

    /// Aggregate health across providers and the Prometheus backend.
    pub async fn health(&self) -> RuntimeHealth {
        check_runtime(&self.manager, DEFAULT_BACKEND_URL).await
    }
}
