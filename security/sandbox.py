from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SandboxExecutionResult:
    code: str
    language: str
    result: Any
    status: str


@dataclass
class PluginValidationResult:
    plugin_path: str
    safe: bool
    status: str


class SandboxManager:
    def execute_isolated(
        self, code: str, language: str = "python", timeout_seconds: int = 5
    ) -> dict[str, Any]:
        result = SandboxExecutionResult(
            code=code, language=language, result=None, status="stub"
        )
        logger.info(
            "Sandbox execute_isolated (stub): language=%s code_len=%d timeout=%d",
            language,
            len(code),
            timeout_seconds,
        )
        return {
            "code": result.code,
            "language": result.language,
            "result": result.result,
            "status": result.status,
        }

    def validate_plugin(self, plugin_path: str) -> dict[str, Any]:
        result = PluginValidationResult(
            plugin_path=plugin_path, safe=True, status="stub"
        )
        logger.info("Sandbox validate_plugin (stub): path=%s", plugin_path)
        return {
            "plugin_path": result.plugin_path,
            "safe": result.safe,
            "status": result.status,
        }
