//! HTTP-backed AI providers — OpenAI-compatible plus Anthropic.
//!
//! A single parameterized [`HttpProvider`] serves every cloud/local provider in
//! the roadmap (OpenAI, Anthropic, Gemini, OpenRouter, Ollama, llama.cpp,
//! vLLM, and user-defined `custom`). They differ only in `base_url`, auth
//! header, request/response shape ([`ApiStyle`]), and default model — so one
//! implementation keeps the per-provider surface consistent and testable.

use async_trait::async_trait;
use futures::stream::{self, BoxStream, StreamExt};
use reqwest::Client;
use serde_json::json;
use std::sync::Arc;
use std::time::Instant;

use crate::error::AetherError;
use crate::provider::Provider;
use crate::types::{ChatRequest, ChatResponse, ProviderHealth, ProviderKind};

/// How a provider's `/chat` and `/models` endpoints are shaped.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ApiStyle {
    /// OpenAI `/v1/chat/completions` + `/v1/models` (also covers Gemini's
    /// OpenAI-compat surface, OpenRouter, Ollama, llama.cpp, vLLM).
    OpenAi,
    /// Anthropic `/v1/messages` (x-api-key auth, distinct request/response).
    Anthropic,
}

/// A provider backed by an HTTP API. Construct via the factory helpers
/// ([`HttpProvider::openai`], [`HttpProvider::anthropic`], ...) or
/// [`HttpProvider::custom`] for a user-defined endpoint.
pub struct HttpProvider {
    id: String,
    name: String,
    kind: ProviderKind,
    base_url: String,
    api_key: Option<String>,
    default_model: String,
    style: ApiStyle,
    static_models: Vec<String>,
    client: Client,
}

impl HttpProvider {
    fn with_keywords(
        id: &str,
        name: &str,
        kind: ProviderKind,
        base_url: &str,
        api_key: Option<String>,
        default_model: &str,
        style: ApiStyle,
        static_models: Vec<String>,
    ) -> Arc<dyn Provider> {
        Arc::new(Self {
            id: id.to_string(),
            name: name.to_string(),
            kind,
            base_url: base_url.trim_end_matches('/').to_string(),
            api_key,
            default_model: default_model.to_string(),
            style,
            static_models,
            client: Client::new(),
        })
    }

    // ---- Factory helpers (Phase 3.1) ----

    pub fn openai(api_key: impl Into<String>) -> Arc<dyn Provider> {
        Self::with_keywords(
            "openai",
            "OpenAI",
            ProviderKind::OpenAi,
            "https://api.openai.com/v1",
            Some(api_key.into()),
            "gpt-4o-mini",
            ApiStyle::OpenAi,
            vec![
                "gpt-4o".into(),
                "gpt-4o-mini".into(),
                "o1".into(),
                "o3-mini".into(),
            ],
        )
    }

    pub fn anthropic(api_key: impl Into<String>) -> Arc<dyn Provider> {
        Self::with_keywords(
            "anthropic",
            "Anthropic",
            ProviderKind::Anthropic,
            "https://api.anthropic.com/v1",
            Some(api_key.into()),
            "claude-3-5-sonnet-latest",
            ApiStyle::Anthropic,
            vec![
                "claude-3-5-sonnet-latest".into(),
                "claude-3-5-opus-latest".into(),
                "claude-3-5-haiku-latest".into(),
            ],
        )
    }

    pub fn gemini(api_key: impl Into<String>) -> Arc<dyn Provider> {
        Self::with_keywords(
            "gemini",
            "Gemini",
            ProviderKind::Gemini,
            "https://generativelanguage.googleapis.com/v1beta/openai",
            Some(api_key.into()),
            "gemini-2.0-flash",
            ApiStyle::OpenAi,
            vec!["gemini-2.5-pro".into(), "gemini-2.0-flash".into()],
        )
    }

    pub fn openrouter(api_key: impl Into<String>) -> Arc<dyn Provider> {
        Self::with_keywords(
            "openrouter",
            "OpenRouter",
            ProviderKind::OpenRouter,
            "https://openrouter.ai/api/v1",
            Some(api_key.into()),
            "openai/gpt-4o-mini",
            ApiStyle::OpenAi,
            vec!["openai/gpt-4o-mini".into(), "anthropic/claude-3.5-sonnet".into()],
        )
    }

    pub fn ollama() -> Arc<dyn Provider> {
        Self::with_keywords(
            "ollama",
            "Ollama",
            ProviderKind::Ollama,
            "http://localhost:11434/v1",
            None,
            "llama3.1",
            ApiStyle::OpenAi,
            vec!["llama3.1".into(), "mistral".into(), "qwen2.5".into()],
        )
    }

    pub fn llamacpp(base_url: Option<&str>) -> Arc<dyn Provider> {
        Self::with_keywords(
            "llamacpp",
            "llama.cpp",
            ProviderKind::LlamaCpp,
            base_url.unwrap_or("http://localhost:8080/v1"),
            None,
            "local",
            ApiStyle::OpenAi,
            vec!["local".into()],
        )
    }

    pub fn vllm(base_url: Option<&str>) -> Arc<dyn Provider> {
        Self::with_keywords(
            "vllm",
            "vLLM",
            ProviderKind::Vllm,
            base_url.unwrap_or("http://localhost:8000/v1"),
            None,
            "local",
            ApiStyle::OpenAi,
            vec!["local".into()],
        )
    }

    /// A user-defined endpoint. `style` selects the request/response contract.
    pub fn custom(
        id: &str,
        name: &str,
        base_url: &str,
        api_key: Option<String>,
        default_model: &str,
        style: ApiStyle,
    ) -> Arc<dyn Provider> {
        Self::with_keywords(
            id,
            name,
            ProviderKind::CustomHttp,
            base_url,
            api_key,
            default_model,
            style,
            vec![default_model.to_string()],
        )
    }

    fn auth_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        match self.style {
            ApiStyle::Anthropic => {
                if let Some(key) = &self.api_key {
                    if let Ok(v) = reqwest::header::HeaderValue::from_str(key) {
                        headers.insert("x-api-key", v);
                    }
                }
                let v = reqwest::header::HeaderValue::from_static("2023-06-01");
                headers.insert("anthropic-version", v);
            }
            ApiStyle::OpenAi => {
                if let Some(key) = &self.api_key {
                    if let Ok(v) = reqwest::header::HeaderValue::from_str(&format!("Bearer {key}"))
                    {
                        headers.insert(reqwest::header::AUTHORIZATION, v);
                    }
                }
            }
        }
        headers
    }

    fn chat_url(&self) -> String {
        match self.style {
            ApiStyle::OpenAi => format!("{}/chat/completions", self.base_url),
            ApiStyle::Anthropic => format!("{}/messages", self.base_url),
        }
    }

    fn models_url(&self) -> String {
        format!("{}/models", self.base_url)
    }

    fn resolve_model<'a>(&'a self, req: &'a ChatRequest) -> &'a str {
        if req.model.is_empty() {
            &self.default_model
        } else {
            &req.model
        }
    }

    /// Build the provider-specific request body and extract content from the
    /// response body.
    fn prepare(
        &self,
        req: &ChatRequest,
    ) -> Result<(serde_json::Value, serde_json::Value), AetherError> {
        let model = self.resolve_model(req);
        match self.style {
            ApiStyle::OpenAi => {
                let payload = json!({
                    "model": model,
                    "messages": req.messages,
                    "stream": false,
                });
                let extractor = json!({
                    "path": ["choices", 0, "message", "content"],
                    "model_path": ["model"],
                });
                Ok((payload, extractor))
            }
            ApiStyle::Anthropic => {
                let mut system_parts: Vec<&str> = Vec::new();
                let messages: Vec<serde_json::Value> = req
                    .messages
                    .iter()
                    .map(|m| {
                        let role = match m.role {
                            crate::types::ChatRole::System => {
                                system_parts.push(m.content.as_str());
                                "user"
                            }
                            crate::types::ChatRole::User => "user",
                            crate::types::ChatRole::Assistant => "assistant",
                            crate::types::ChatRole::Tool => "user",
                        };
                        json!({ "role": role, "content": m.content })
                    })
                    .collect();
                let mut payload = json!({
                    "model": model,
                    "max_tokens": 4096,
                    "messages": messages,
                });
                if !system_parts.is_empty() {
                    payload["system"] = json!(system_parts.join("\n"));
                }
                let extractor = json!({
                    "content_array_path": ["content"],
                    "model_path": ["model"],
                });
                Ok((payload, extractor))
            }
        }
    }

    fn extract_content(
        &self,
        value: &serde_json::Value,
        extractor: &serde_json::Value,
    ) -> Result<(String, String), AetherError> {
        let model = extractor
            .get("model_path")
            .and_then(|p| p.as_array())
            .map(|p| json_pointer(p))
            .and_then(|p| value.pointer(&p))
            .and_then(|m| m.as_str())
            .map(str::to_string)
            .unwrap_or_default();

        let content = if let Some(arr_path) = extractor.get("content_array_path") {
            let path = json_pointer(arr_path.as_array().unwrap_or(&vec![]));
            value
                .pointer(&path)
                .and_then(|c| c.as_array())
                .map(|blocks| {
                    blocks
                        .iter()
                        .filter_map(|b| b.get("text").and_then(|t| t.as_str()))
                        .collect::<Vec<_>>()
                        .join("")
                })
                .ok_or_else(|| {
                    AetherError::Provider("anthropic response missing content[]".into())
                })?
        } else {
            let path = extractor
                .get("path")
                .and_then(|p| p.as_array())
                .map(|p| json_pointer(p))
                .unwrap_or_else(|| "choices/0/message/content".into());
            value
                .pointer(&path)
                .and_then(|c| c.as_str())
                .map(str::to_string)
                .ok_or_else(|| {
                    AetherError::Provider(format!("provider response missing {path}"))
                })?
        };
        Ok((content, model))
    }

    /// Stream a chat completion, yielding text deltas. OpenAI-style SSE only;
    /// Anthropic streams are normalized to the same delta shape.
    pub async fn stream_chat(
        &self,
        req: ChatRequest,
    ) -> BoxStream<'static, Result<String, AetherError>> {
        let client = self.client.clone();
        let headers = self.auth_headers();
        let url = self.chat_url();
        let model = self.resolve_model(&req).to_string();
        let (payload, _) = match self.prepare(&req) {
            Ok(v) => v,
            Err(e) => return stream::once(async move { Err(e) }).boxed(),
        };

        let fut = async move {
            let resp = client
                .post(&url)
                .headers(headers)
                .json(&payload)
                .send()
                .await?;
            if !resp.status().is_success() {
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                return Err(AetherError::Provider(format!(
                    "provider chat failed ({status}): {body}"
                )));
            }
            let stream = resp.bytes_stream();
            let mapped = stream.filter_map(move |chunk| {
                let model = model.clone();
                async move {
                    let bytes = chunk.ok()?;
                    let text = String::from_utf8_lossy(&bytes);
                    parse_sse_delta(&text, model.as_str())
                }
            });
            Ok(mapped)
        };

        match fut.await {
            Ok(s) => s
                .map(|r: Result<String, AetherError>| r)
                .boxed(),
            Err(e) => stream::once(async move { Err(e) }).boxed(),
        }
    }
}

/// Pull a content delta out of one SSE frame. Returns `None` for non-content
/// frames (role markers, done, errors).
fn parse_sse_delta(frame: &str, model: &str) -> Option<Result<String, AetherError>> {
    for line in frame.lines() {
        let line = line.trim();
        if !line.starts_with("data:") {
            continue;
        }
        let data = line.trim_start_matches("data:").trim();
        if data == "[DONE]" {
            return None;
        }
        let value: serde_json::Value = match serde_json::from_str(data) {
            Ok(v) => v,
            Err(_) => continue,
        };
        if let Some(err) = value.get("error") {
            return Some(Err(AetherError::Provider(format!("stream error: {err}"))));
        }
        if let Some(content) = value
            .pointer("/choices/0/delta/content")
            .and_then(|c| c.as_str())
        {
            if !content.is_empty() {
                return Some(Ok(content.to_string()));
            }
        }
    }
    let _ = model;
    None
}

/// Render a JSON-pointer path from a list of token values, handling integer
/// tokens (e.g. array indices) that `as_str()` would drop to an empty string.
/// serde_json's `pointer` follows RFC 6901 and requires a leading `/`.
fn json_pointer(tokens: &[serde_json::Value]) -> String {
    let joined = tokens
        .iter()
        .map(|t| match t {
            serde_json::Value::String(s) => s.clone(),
            other => other.to_string().trim_matches('"').to_string(),
        })
        .collect::<Vec<_>>()
        .join("/");
    format!("/{joined}")
}

#[async_trait]
impl Provider for HttpProvider {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> ProviderKind {
        self.kind
    }

    fn name(&self) -> &str {
        &self.name
    }

    async fn health(&self) -> ProviderHealth {
        let start = Instant::now();
        let resp = self
            .client
            .get(self.models_url())
            .headers(self.auth_headers())
            .send()
            .await;
        match resp {
            Ok(r) => {
                let latency = start.elapsed().as_millis();
                if r.status().is_success() {
                    ProviderHealth::ok(latency)
                } else {
                    ProviderHealth::err(format!("GET /models returned {}", r.status()))
                }
            }
            Err(e) => ProviderHealth::err(format!("{} unreachable: {e}", self.id)),
        }
    }

    async fn chat(&self, req: ChatRequest) -> Result<ChatResponse, AetherError> {
        let (payload, extractor) = self.prepare(&req)?;
        let resp = self
            .client
            .post(self.chat_url())
            .headers(self.auth_headers())
            .json(&payload)
            .send()
            .await?;
        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(AetherError::Provider(format!(
                "provider chat failed ({status}): {body}"
            )));
        }
        let value: serde_json::Value = resp.json().await?;
        let (content, model) = self.extract_content(&value, &extractor)?;
        Ok(ChatResponse {
            content,
            tool_calls: None,
            model: if model.is_empty() {
                self.resolve_model(&req).to_string()
            } else {
                model
            },
        })
    }

    async fn list_models(&self) -> Result<Vec<String>, AetherError> {
        if self.style == ApiStyle::Anthropic {
            return Ok(self.static_models.clone());
        }
        let resp = self
            .client
            .get(self.models_url())
            .headers(self.auth_headers())
            .send()
            .await?;
        if !resp.status().is_success() {
            return Ok(self.static_models.clone());
        }
        let value: serde_json::Value = resp.json().await?;
        let models = value
            .get("data")
            .and_then(|d| d.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|m| m.get("id").and_then(|id| id.as_str()).map(str::to_string))
                    .collect()
            })
            .unwrap_or_else(|| self.static_models.clone());
        Ok(models)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use httpmock::prelude::*;

    #[tokio::test]
    async fn openai_chat_returns_content() {
        let server = MockServer::start();
        let chat = server.mock(|when, then| {
            when.method(POST).path("/chat/completions");
            then.status(200).json_body(json!({
                "model": "gpt-4o-mini",
                "choices": [{"message": {"content": "hello from openai"}}],
            }));
        });
        let provider = HttpProvider::custom(
            "openai-test",
            "OpenAI Test",
            &server.base_url(),
            Some("sk-test".into()),
            "gpt-4o-mini",
            ApiStyle::OpenAi,
        );
        let resp = provider
            .chat(ChatRequest::from_prompt("gpt-4o-mini", "hi"))
            .await
            .unwrap();
        assert_eq!(resp.content, "hello from openai");
        assert_eq!(resp.model, "gpt-4o-mini");
        chat.assert();
    }

    #[tokio::test]
    async fn anthropic_chat_translates_shape() {
        let server = MockServer::start();
        let chat = server.mock(|when, then| {
            when.method(POST).path("/messages");
            then.status(200).json_body(json!({
                "model": "claude-3-5-sonnet-latest",
                "content": [{"type": "text", "text": "hello from anthropic"}],
            }));
        });
        let provider = HttpProvider::custom(
            "anthropic-test",
            "Anthropic Test",
            &server.base_url(),
            Some("key".into()),
            "claude-3-5-sonnet-latest",
            ApiStyle::Anthropic,
        );
        let resp = provider
            .chat(ChatRequest::from_prompt("claude-3-5-sonnet-latest", "hi"))
            .await
            .unwrap();
        assert_eq!(resp.content, "hello from anthropic");
        chat.assert();
    }

    #[tokio::test]
    async fn list_models_falls_back_to_static() {
        let server = MockServer::start();
        server.mock(|when, then| {
            when.method(GET).path("/models");
            then.status(500);
        });
        let provider = HttpProvider::openai("sk-test");
        let models = provider.list_models().await.unwrap();
        assert!(models.contains(&"gpt-4o".to_string()));
    }

    #[tokio::test]
    async fn health_reports_unreachable() {
        let server = MockServer::start();
        server.mock(|when, then| {
            when.method(GET).path("/models");
            then.status(500);
        });
        let provider = HttpProvider::custom(
            "down",
            "Down",
            &server.base_url(),
            None,
            "local",
            ApiStyle::OpenAi,
        );
        let h = provider.health().await;
        assert!(!h.ok);
    }
}
