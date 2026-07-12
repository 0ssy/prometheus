from unittest.mock import MagicMock, patch

import pytest

from services.llm_client import LLMClient


def test_is_configured_true():
    client = LLMClient(base_url="http://localhost:1234/v1", model="local-model")
    assert client.is_configured() is True


def test_is_configured_false_no_model():
    client = LLMClient(base_url="http://localhost:1234/v1", model="")
    assert client.is_configured() is False


def test_is_configured_false_no_url():
    client = LLMClient(base_url="", model="local-model")
    assert client.is_configured() is False


def test_chat_posts_openai_payload():
    client = LLMClient(base_url="http://localhost:1234/v1", model="local-model")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "hello world"}}]
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("services.llm_client.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        result = client.chat(system="be helpful", user="hi")
    assert result == "hello world"
    mock_client_cls.return_value.__enter__.return_value.post.assert_called_once()
    call_args = mock_client_cls.return_value.__enter__.return_value.post.call_args
    assert call_args.args[0] == "http://localhost:1234/v1/chat/completions"
    payload = call_args.kwargs["json"]
    assert payload["model"] == "local-model"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"


def test_chat_raises_when_not_configured():
    client = LLMClient(base_url="", model="")
    with pytest.raises(RuntimeError):
        client.chat(system="s", user="u")


def test_list_models():
    client = LLMClient(base_url="http://localhost:1234/v1", model="local-model")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": [{"id": "model-a"}, {"id": "model-b"}]}
    mock_resp.raise_for_status = MagicMock()
    with patch("services.llm_client.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = client.list_models()
    assert len(result) == 2
    assert result[0]["id"] == "model-a"
