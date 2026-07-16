//! Project Aether — Rust AI Runtime.
//!
//! Abstraction layer over AI providers, intended to live *alongside* the
//! Python Prometheus platform. Provides the provider model (local + cloud),
//! an in-memory manager/registry, a backend-aware health checker, a model
//! router, a context engine, a tool dispatcher, and specialist agent
//! descriptors. The tool/context surfaces talk to the Python backend over its
//! REST API.

pub mod agent;
pub mod context;
pub mod error;
pub mod health;
pub mod http_provider;
pub mod lm_studio;
pub mod manager;
pub mod provider;
pub mod registry;
pub mod routing;
pub mod titan_provider;
pub mod tools;
pub mod types;

pub use agent::{Agent, AgentRole, registry as agent_registry};
pub use context::{Context, ContextEngine};
pub use error::AetherError;
pub use health::check_runtime;
pub use http_provider::{ApiStyle, HttpProvider};
pub use manager::ProviderManager;
pub use provider::Provider;
pub use registry::ProviderRegistry;
pub use routing::{Capability, ModelRouter, RoutingPolicy};
pub use titan_provider::TitanProvider;
pub use tools::ToolDispatcher;
pub use types::{
    ChatMessage, ChatRequest, ChatResponse, ChatRole, ProviderHealth, ProviderInfo, ProviderKind,
    RuntimeHealth,
};

/// Default Prometheus backend address the sidecar listens on.
pub const DEFAULT_BACKEND_URL: &str = "http://127.0.0.1:8000";

/// Runtime bundle shared with the Tauri command surface.
#[derive(Clone)]
pub struct AetherRuntime {
    pub manager: ProviderManager,
    pub router: ModelRouter,
    pub context: ContextEngine,
    pub tools: ToolDispatcher,
}

impl Default for AetherRuntime {
    fn default() -> Self {
        Self::new()
    }
}

impl AetherRuntime {
    /// Build a runtime with the default provider set: all local providers
    /// (LM Studio, Ollama, llama.cpp, vLLM) so the runtime is useful with
    /// zero cloud configuration, plus any cloud provider whose API key is
    /// present in the environment.
    pub fn new() -> Self {
        let manager = ProviderManager::new();

        manager.register(lm_studio::LmStudioProvider::default_local());
        manager.register(HttpProvider::ollama());
        manager.register(HttpProvider::llamacpp(None));
        manager.register(HttpProvider::vllm(None));

        manager.register(TitanProvider::new(None));

        if let Ok(key) = std::env::var("OPENAI_API_KEY") {
            manager.register(HttpProvider::openai(key));
        }
        if let Ok(key) = std::env::var("ANTHROPIC_API_KEY") {
            manager.register(HttpProvider::anthropic(key));
        }
        if let Ok(key) = std::env::var("GEMINI_API_KEY") {
            manager.register(HttpProvider::gemini(key));
        }
        if let Ok(key) = std::env::var("OPENROUTER_API_KEY") {
            manager.register(HttpProvider::openrouter(key));
        }

        Self {
            manager,
            router: ModelRouter::new(),
            context: ContextEngine::new(),
            tools: ToolDispatcher::with_backend(DEFAULT_BACKEND_URL),
        }
    }

    /// Build a runtime pointed at a specific backend (e.g. the test sidecar).
    pub fn with_backend(backend_url: &str) -> Self {
        let mut rt = Self::new();
        rt.tools = ToolDispatcher::with_backend(backend_url);
        rt.context = ContextEngine::with_backend(backend_url);
        rt
    }

    /// Resolve the provider that should serve a request, applying the active
    /// routing policy.
    pub fn route(
        &self,
        requested: Option<&str>,
        capability: Option<Capability>,
    ) -> Option<String> {
        self.router.select(&self.manager, requested, capability)
    }

    /// Aggregate health across providers and the Prometheus backend.
    pub async fn health(&self) -> RuntimeHealth {
        check_runtime(&self.manager, DEFAULT_BACKEND_URL).await
    }
}

#[cfg(feature = "python")]
mod pybind {
    use pyo3::prelude::*;

    #[pyfunction]
    fn version() -> &'static str {
        env!("CARGO_PKG_VERSION")
    }

    #[pymodule]
    fn aether_runtime(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(version, m)?)?;
        m.add("__version__", env!("CARGO_PKG_VERSION"))?;
        Ok(())
    }
}
