//! LM Studio provider — OpenAI-compatible `/v1/chat/completions` + `/v1/models`.

use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;
use std::sync::Arc;
use std::time::Instant;

use crate::error::AetherError;
use crate::provider::Provider;
use crate::types::{ChatRequest, ChatResponse, ProviderHealth, ProviderKind};

const DEFAULT_BASE_URL: &str = "http://localhost:1234";
const FALLBACK_MODEL: &str = "local-model";

/// A provider backed by a local LM Studio instance.
///
/// LM Studio exposes an OpenAI-compatible API, so this implementation is the
/// template later stages reuse for OpenAI/OpenRouter/Gemini (differing only in
/// base URL, auth, and model naming).
pub struct LmStudioProvider {
    id: String,
    name: String,
    base_url: String,
    api_key: Option<String>,
    client: Client,
}

impl LmStudioProvider {
    pub fn new(name: impl Into<String>, base_url: Option<String>) -> Self {
        Self::with_api_key(name, base_url, None)
    }

    pub fn with_api_key(
        name: impl Into<String>,
        base_url: Option<String>,
        api_key: Option<String>,
    ) -> Self {
        Self {
            id: "lmstudio".to_string(),
            name: name.into(),
            base_url: base_url.unwrap_or_else(|| DEFAULT_BASE_URL.to_string()),
            api_key,
            client: Client::new(),
        }
    }

    /// Convenience: a default LM Studio provider at the standard local port.
    pub fn default_local() -> Arc<dyn Provider> {
        Arc::new(Self::new("LM Studio", None))
    }

    fn auth_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        if let Some(key) = &self.api_key {
            if let Ok(value) = reqwest::header::HeaderValue::from_str(&format!("Bearer {key}")) {
                headers.insert(reqwest::header::AUTHORIZATION, value);
            }
        }
        headers
    }
}

#[async_trait]
impl Provider for LmStudioProvider {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> ProviderKind {
        ProviderKind::LmStudio
    }

    fn name(&self) -> &str {
        &self.name
    }

    async fn health(&self) -> ProviderHealth {
        let url = format!("{}/v1/models", self.base_url);
        let start = Instant::now();
        match self
            .client
            .get(&url)
            .headers(self.auth_headers())
            .send()
            .await
        {
            Ok(resp) => {
                let latency = start.elapsed().as_millis();
                if resp.status().is_success() {
                    ProviderHealth::ok(latency)
                } else {
                    ProviderHealth::err(format!("GET /v1/models returned {}", resp.status()))
                }
            }
            Err(e) => ProviderHealth::err(format!("lm studio unreachable: {e}")),
        }
    }

    async fn chat(&self, req: ChatRequest) -> Result<ChatResponse, AetherError> {
        let url = format!("{}/v1/chat/completions", self.base_url);
        let model = if req.model.is_empty() {
            FALLBACK_MODEL.to_string()
        } else {
            req.model.clone()
        };

        let payload = json!({
            "model": model,
            "messages": req.messages,
            "stream": false,
        });

        let resp = self
            .client
            .post(&url)
            .headers(self.auth_headers())
            .json(&payload)
            .send()
            .await?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(AetherError::Provider(format!(
                "lm studio chat failed ({status}): {body}"
            )));
        }

        let value: serde_json::Value = resp.json().await?;
        let content = value
            .get("choices")
            .and_then(|c| c.get(0))
            .and_then(|c| c.get("message"))
            .and_then(|m| m.get("content"))
            .and_then(|c| c.as_str())
            .ok_or_else(|| {
                AetherError::Provider(
                    "lm studio response missing choices[0].message.content".to_string(),
                )
            })?
            .to_string();

        let echoed_model = value
            .get("model")
            .and_then(|m| m.as_str())
            .map(|s| s.to_string())
            .unwrap_or(model);

        Ok(ChatResponse {
            content,
            tool_calls: None,
            model: echoed_model,
        })
    }

    async fn list_models(&self) -> Result<Vec<String>, AetherError> {
        let url = format!("{}/v1/models", self.base_url);
        let resp = self
            .client
            .get(&url)
            .headers(self.auth_headers())
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(AetherError::Provider(format!(
                "lm studio list_models failed: {}",
                resp.status()
            )));
        }

        let value: serde_json::Value = resp.json().await?;
        let models = value
            .get("data")
            .and_then(|d| d.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|m| {
                        m.get("id")
                            .and_then(|id| id.as_str())
                            .map(|s| s.to_string())
                    })
                    .collect()
            })
            .unwrap_or_default();

        Ok(models)
    }
}
