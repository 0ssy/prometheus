//! Integration tests for the LM Studio provider against a mocked
//! OpenAI-compatible HTTP surface (httpmock).

use aether_runtime::lm_studio::LmStudioProvider;
use aether_runtime::provider::Provider;
use aether_runtime::types::ChatRequest;
use std::sync::Arc;

#[tokio::test]
async fn chat_parses_content_and_echoes_model() {
    let server = httpmock::MockServer::start();
    let chat = server.mock(|when, then| {
        when.method(httpmock::Method::POST)
            .path("/v1/chat/completions");
        then.status(200).json_body(serde_json::json!({
            "id": "x",
            "object": "chat.completion",
            "model": "llama-3",
            "choices": [{
                "index": 0,
                "message": { "role": "assistant", "content": "hello from model" },
                "finish_reason": "stop"
            }],
            "usage": { "prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3 }
        }));
    });
    let models = server.mock(|when, then| {
        when.method(httpmock::Method::GET).path("/v1/models");
        then.status(200).json_body(serde_json::json!({
            "object": "list",
            "data": [ { "id": "llama-3" }, { "id": "mistral" } ]
        }));
    });

    let provider = Arc::new(LmStudioProvider::new("LM Studio", Some(server.base_url())));

    let resp = provider
        .chat(ChatRequest::from_prompt("llama-3", "ping"))
        .await
        .expect("chat should succeed");
    assert_eq!(resp.content, "hello from model");
    assert_eq!(resp.model, "llama-3");

    let listed = provider.list_models().await.expect("list_models");
    assert_eq!(listed, vec!["llama-3".to_string(), "mistral".to_string()]);

    chat.assert();
    models.assert();
}

#[tokio::test]
async fn health_ok_on_models_endpoint() {
    let server = httpmock::MockServer::start();
    server.mock(|when, then| {
        when.method(httpmock::Method::GET).path("/v1/models");
        then.status(200)
            .json_body(serde_json::json!({ "object": "list", "data": [] }));
    });

    let provider = Arc::new(LmStudioProvider::new("LM Studio", Some(server.base_url())));
    let health = provider.health().await;
    assert!(health.ok);
    assert!(health.latency_ms.is_some());
}

#[tokio::test]
async fn health_err_on_connection_refused() {
    let provider = Arc::new(LmStudioProvider::new(
        "LM Studio",
        Some("http://127.0.0.1:1".to_string()),
    ));
    let health = provider.health().await;
    assert!(!health.ok);
    assert!(health.detail.is_some());
}

#[tokio::test]
async fn chat_falls_back_to_local_model_when_empty() {
    let server = httpmock::MockServer::start();
    let chat = server.mock(|when, then| {
        when.method(httpmock::Method::POST)
            .path("/v1/chat/completions")
            .body_contains("local-model");
        then.status(200).json_body(serde_json::json!({
            "model": "local-model",
            "choices": [{
                "index": 0,
                "message": { "role": "assistant", "content": "ok" },
                "finish_reason": "stop"
            }]
        }));
    });

    let provider = Arc::new(LmStudioProvider::new("LM Studio", Some(server.base_url())));
    let resp = provider
        .chat(ChatRequest::from_prompt("", "ping"))
        .await
        .expect("chat should succeed");
    assert_eq!(resp.content, "ok");
    chat.assert();
}

#[tokio::test]
async fn check_runtime_aggregates_providers_and_backend() {
    use aether_runtime::health::check_runtime;
    use aether_runtime::ProviderManager;

    let provider_server = httpmock::MockServer::start();
    provider_server.mock(|when, then| {
        when.method(httpmock::Method::GET).path("/v1/models");
        then.status(200)
            .json_body(serde_json::json!({ "object": "list", "data": [] }));
    });

    let backend = httpmock::MockServer::start();
    backend.mock(|when, then| {
        when.method(httpmock::Method::GET).path("/health");
        then.status(200).json_body(serde_json::json!({ "ok": true }));
    });

    let manager = ProviderManager::new();
    manager.register(Arc::new(LmStudioProvider::new("LM Studio", Some(provider_server.base_url()))));

    let health = check_runtime(&manager, &backend.base_url()).await;
    assert_eq!(health.providers.len(), 1);
    assert!(health.providers[0].ok);
    assert!(health.backend.ok);
}
