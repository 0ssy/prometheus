from unittest.mock import MagicMock, patch

import pytest

from backend.main import assistant_query


def test_assistant_no_lm_returns_message():
    mock_llm = MagicMock()
    mock_llm.is_configured.return_value = False
    with patch("backend.main.LLMClient", return_value=mock_llm):
        result = assistant_query(payload={"prompt": "hello"}, container=MagicMock())
    assert "language model configured" in result["response"]


def test_assistant_llm_configured_calls_chat():
    mock_llm = MagicMock()
    mock_llm.is_configured.return_value = True
    mock_llm.chat.return_value = "mocked llm response"
    with patch("backend.main.LLMClient", return_value=mock_llm):
        result = assistant_query(payload={"prompt": "what is prometheus"}, container=MagicMock())
    assert result["response"] == "mocked llm response"
    mock_llm.chat.assert_called_once()
    call_kwargs = mock_llm.chat.call_args.kwargs
    assert "Prometheus" in call_kwargs["system"]
    assert call_kwargs["user"] == "what is prometheus"


def test_assistant_requires_prompt():
    with pytest.raises(RuntimeError):
        assistant_query(payload={}, container=MagicMock())
