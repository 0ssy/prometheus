
import httpx

from core.config import config
from core.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """OpenAI-compatible chat client for local providers (LM Studio, Ollama, etc.)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url if base_url is not None else config.llm_base_url
        self.base_url = self.base_url.rstrip("/")
        self.model = model if model is not None else config.llm_model
        self.api_key = api_key if api_key is not None else config.llm_api_key
        self._timeout = httpx.Timeout(60.0, connect=5.0)

    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)

    def chat(self, system: str, user: str) -> str:
        if not self.is_configured():
            raise RuntimeError(
                "No language model configured. Set PROMETHEUS_LLM_BASE_URL and "
                "PROMETHEUS_LLM_MODEL, or run with an OpenAI-compatible provider "
                "(e.g. LM Studio)."
            )
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        logger.info("LLM request -> %s/chat/completions model=%s", self.base_url, self.model)
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info("LLM response length=%d", len(content))
        return content

    def list_models(self) -> list[dict]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self.base_url}/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data.get("data", [])
