//! Titan provider — tokenization and fine-tuning capabilities via the
//! Prometheus Python backend.
//!
//! The Titan provider is a thin wrapper around the `/titan/execute` endpoint.
//! It exposes tokenizer workflows (encode/decode) as provider-level
//! operations so the Aether runtime can dispatch them through the normal
//! provider routing layer.

use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;
use std::sync::Arc;
use std::time::Instant;

use crate::error::AetherError;
use crate::types::{ChatRequest, ChatResponse, ProviderHealth, ProviderKind};
use crate::DEFAULT_BACKEND_URL;

#[derive(Debug, Clone)]
pub struct TitanProvider {
    id: String,
    name: String,
    kind: ProviderKind,
    base_url: String,
    client: Client,
}

impl TitanProvider {
    pub fn new(base_url: Option<&str>) -> Arc<dyn crate::Provider> {
        Arc::new(Self {
            id: "titan".into(),
            name: "Titan AI Platform".into(),
            kind: ProviderKind::CustomHttp,
            base_url: base_url.unwrap_or(DEFAULT_BACKEND_URL).trim_end_matches('/').to_string(),
            client: Client::new(),
        })
    }

    async fn call_titan(&self, module: &str, workflow: &str, payload: serde_json::Value) -> Result<serde_json::Value, AetherError> {
        let url = format!("{}/titan/execute", self.base_url);
        let body = json!({
            "module_name": module,
            "workflow": workflow,
            "payload": payload,
        });
        let start = Instant::now();
        let res = self.client.post(&url).json(&body).send().await.map_err(|e| {
            AetherError::Provider(format!("titan request failed: {e}"))
        })?;
        let latency = start.elapsed();
        if !res.status().is_success() {
            return Err(AetherError::Provider(format!(
                "titan endpoint returned {}",
                res.status()
            )));
        }
        let data: serde_json::Value = res.json().await.map_err(|e| {
            AetherError::Provider(format!("titan response parse failed: {e}"))
        })?;
        Ok(data)
    }
}

#[async_trait]
impl crate::Provider for TitanProvider {
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
        match self.call_titan("dataset_builder", "get", json!({"dataset_id": "health-check"})).await {
            Ok(_) => ProviderHealth {
                ok: true,
                latency_ms: Some(start.elapsed().as_millis()),
                detail: Some("titan backend reachable".into()),
            },
            Err(_) => ProviderHealth {
                ok: false,
                latency_ms: Some(start.elapsed().as_millis()),
                detail: Some("titan backend unreachable".into()),
            },
        }
    }

    async fn chat(&self, req: ChatRequest) -> Result<ChatResponse, AetherError> {
        let model = if req.model.is_empty() { "titan" } else { &req.model };
        let prompt = req.messages.last().map(|m| m.content.as_str()).unwrap_or("");
        let result = self.call_titan("tokenizer", "encode", json!({"text": prompt})).await?;
        let ids = result
            .get("data")
            .and_then(|d| d.get("ids"))
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_u64()).collect::<Vec<u64>>())
            .unwrap_or_default();
        Ok(ChatResponse {
            content: format!("encoded {} tokens", ids.len()),
            tool_calls: None,
            model: model.into(),
        })
    }

    async fn list_models(&self) -> Result<Vec<String>, AetherError> {
        Ok(vec![
            "titan-tokenizer".into(),
            "titan-finetune".into(),
            "titan-evaluation".into(),
            "titan-quantization".into(),
            "titan-registry".into(),
            "titan-experiments".into(),
        ])
    }
}
