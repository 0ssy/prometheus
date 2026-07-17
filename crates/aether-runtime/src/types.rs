//! Core data types shared across the Aether AI Runtime.

use crate::agent::AgentRole;
use serde::{Deserialize, Serialize};

/// The role of a participant in a chat conversation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ChatRole {
    System,
    User,
    Assistant,
    Tool,
}

/// A single message in a chat conversation.
///
/// Kept OpenAI-shaped so it can be forwarded to an OpenAI-compatible endpoint
/// (`/v1/chat/completions`) without transformation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: ChatRole,
    pub content: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

impl ChatMessage {
    pub fn system(content: impl Into<String>) -> Self {
        Self {
            role: ChatRole::System,
            content: content.into(),
            name: None,
        }
    }

    pub fn user(content: impl Into<String>) -> Self {
        Self {
            role: ChatRole::User,
            content: content.into(),
            name: None,
        }
    }

    pub fn assistant(content: impl Into<String>) -> Self {
        Self {
            role: ChatRole::Assistant,
            content: content.into(),
            name: None,
        }
    }
}

/// A chat completion request sent to a provider.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatRequest {
    /// Target model name. Empty string falls back to the provider default.
    #[serde(default)]
    pub model: String,
    pub messages: Vec<ChatMessage>,
    /// Reserved for Stage 5 tool calling; unused in M1.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tools: Option<Vec<serde_json::Value>>,
    /// Reserved for Stage 7 streaming; unused in M1.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stream: Option<bool>,
}

impl ChatRequest {
    /// Build a single-turn request from a user prompt against `model`.
    pub fn from_prompt(model: impl Into<String>, prompt: impl Into<String>) -> Self {
        Self {
            model: model.into(),
            messages: vec![ChatMessage::user(prompt)],
            tools: None,
            stream: None,
        }
    }
}

/// A chat completion response returned by a provider.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    /// The assistant text content.
    pub content: String,
    /// Reserved for Stage 5 tool calls; always `None` in M1.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<serde_json::Value>>,
    /// The model that produced the response (echoed from the request when unknown).
    pub model: String,
}

/// Health snapshot for a single provider (or the backend).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderHealth {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub latency_ms: Option<u128>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
}

impl ProviderHealth {
    pub fn ok(latency_ms: u128) -> Self {
        Self {
            ok: true,
            latency_ms: Some(latency_ms),
            detail: None,
        }
    }

    pub fn err(detail: impl Into<String>) -> Self {
        Self {
            ok: false,
            latency_ms: None,
            detail: Some(detail.into()),
        }
    }
}

/// The kind of AI provider. `LmStudio` is the local default; the HTTP-backed
/// providers (`OpenAi`, `Anthropic`, `Gemini`, `OpenRouter`, `Ollama`,
/// `LlamaCpp`, `Vllm`, `CustomHttp`) are served by the shared `HttpProvider`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ProviderKind {
    LmStudio,
    OpenAi,
    Anthropic,
    Gemini,
    OpenRouter,
    Ollama,
    LlamaCpp,
    Vllm,
    CustomHttp,
}

impl ProviderKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            ProviderKind::LmStudio => "lmstudio",
            ProviderKind::OpenAi => "openai",
            ProviderKind::Anthropic => "anthropic",
            ProviderKind::Gemini => "gemini",
            ProviderKind::OpenRouter => "openrouter",
            ProviderKind::Ollama => "ollama",
            ProviderKind::LlamaCpp => "llamacpp",
            ProviderKind::Vllm => "vllm",
            ProviderKind::CustomHttp => "customhttp",
        }
    }
}

/// Lightweight description of a registered provider for listing in the Tauri UI.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderInfo {
    pub id: String,
    pub kind: ProviderKind,
    pub name: String,
    pub default: bool,
}

/// Aggregated health across all providers and the Prometheus backend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeHealth {
    pub providers: Vec<ProviderHealth>,
    pub backend: ProviderHealth,
}

/// Per-provider cost accumulator.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CostAccumulator {
    pub total_tokens: u64,
    pub prompt_tokens: u64,
    pub completion_tokens: u64,
    pub requests: u64,
    pub total_cost_usd: f64,
}

impl CostAccumulator {
    pub fn record(&mut self, prompt_tokens: u64, completion_tokens: u64, cost_per_1k: f64) {
        self.prompt_tokens += prompt_tokens;
        self.completion_tokens += completion_tokens;
        self.total_tokens += prompt_tokens + completion_tokens;
        self.requests += 1;
        self.total_cost_usd += ((prompt_tokens + completion_tokens) as f64 / 1000.0) * cost_per_1k;
    }
}

/// Agent lifecycle state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AgentState {
    Idle,
    Running,
    Paused,
    Failed,
    Killed,
}

/// Agent heartbeat metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentHeartbeat {
    pub role: AgentRole,
    pub state: AgentState,
    pub last_seen: String,
    pub task: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chat_request_round_trip() {
        let req = ChatRequest::from_prompt("local-model", "hello");
        let json = serde_json::to_string(&req).unwrap();
        let back: ChatRequest = serde_json::from_str(&json).unwrap();
        assert_eq!(back.model, "local-model");
        assert_eq!(back.messages.len(), 1);
        assert_eq!(back.messages[0].role, ChatRole::User);
        assert_eq!(back.messages[0].content, "hello");
    }

    #[test]
    fn chat_response_round_trip() {
        let resp = ChatResponse {
            content: "hi".into(),
            tool_calls: None,
            model: "local-model".into(),
        };
        let json = serde_json::to_string(&resp).unwrap();
        let back: ChatResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(back.content, "hi");
        assert_eq!(back.model, "local-model");
    }

    #[test]
    fn provider_kind_serializes_lowercase() {
        assert_eq!(
            serde_json::to_string(&ProviderKind::LmStudio).unwrap(),
            "\"lmstudio\""
        );
    }
}
