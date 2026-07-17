//! The [`Provider`] trait — the core abstraction every AI backend implements.

use async_trait::async_trait;

use crate::error::AetherError;
use crate::types::{ChatRequest, ChatResponse, ProviderHealth, ProviderKind};

/// An AI provider capable of health checks, chat completion, and model listing.
///
/// Implementations are stored as `Box<dyn Provider>` behind interior mutability
/// in the [`crate::registry::ProviderRegistry`]. Trait objects must be `Send +
/// Sync` because the Tauri runtime shares them across the async command surface.
#[async_trait]
pub trait Provider: Send + Sync {
    /// Stable unique identifier (e.g. `"lmstudio"`).
    fn id(&self) -> &str;

    /// The provider family, used for listing and later stage routing.
    fn kind(&self) -> ProviderKind;

    /// Human-friendly display name.
    fn name(&self) -> &str;

    /// Liveness/health probe. Implementations measure and report latency.
    async fn health(&self) -> ProviderHealth;

    /// Run a chat completion request.
    async fn chat(&self, req: ChatRequest) -> Result<ChatResponse, AetherError>;

    /// List the model identifiers exposed by the provider.
    async fn list_models(&self) -> Result<Vec<String>, AetherError>;

    /// Estimated cost per 1K tokens for this provider (USD).
    fn cost_per_1k(&self) -> f64 {
        0.0
    }
}
