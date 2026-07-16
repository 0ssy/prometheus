"""
Prometheus Logging System
-------------------------
Every module gets a logger via get_logger(__name__). Logs go to both
console and a file so you have a persistent research/debug trail —
this matters later when Prometheus is reasoning about hardware and
you need to reconstruct what it did and why.

The file sink is machine-readable JSON lines (one JSON object per
line) with secret redaction applied, so the persisted log can be
streamed/ingested safely and never leaks credentials.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone

from .config import config


# Configured secret values are masked wherever they appear in a message.
def _configured_secrets() -> list[str]:
    secrets = [config.llm_api_key]
    return [s for s in secrets if s]


# Key-shaped / credential-bearing substrings that should never hit the file.
_TOKEN_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9._\-]+|eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)"
)
_KV_PATTERN = re.compile(
    r"(?i)(api[_-]?key|apikey|token|secret|password|passwd|authorization|session[_-]?id)"
    r"\s*[:=]\s*['\"]?([^\s'\"]+)"
)

_MASK = "***REDACTED***"


def _redact(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    out = text
    for secret in _configured_secrets():
        if secret and secret in out:
            out = out.replace(secret, _MASK)
    out = _TOKEN_PATTERN.sub(_MASK, out)
    out = _KV_PATTERN.sub(lambda m: f"{m.group(1)}= {_MASK}", out)
    return out


def _redact_arg(value: object) -> object:
    """Redact only string args; preserve numbers/other types so %-formatting
    (e.g. ``%.2fs``) keeps working."""
    if isinstance(value, str):
        return _redact(value)
    return value


class RedactingFilter(logging.Filter):
    """Strips secrets from the message and any args before emit."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(str(record.msg))
        args = record.args
        if isinstance(args, dict):
            record.args = {k: _redact_arg(v) for k, v in args.items()}
        elif isinstance(args, tuple):
            record.args = tuple(_redact_arg(v) for v in args)
        return True


class JsonLineFormatter(logging.Formatter):
    """Emits one JSON object per log line (no embedded newlines)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        line = json.dumps(payload, ensure_ascii=False)
        return line.replace("\n", "\\n")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured (avoids duplicate handlers on re-import)
        return logger

    logger.setLevel(config.log_level)
    logger.addFilter(RedactingFilter())

    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    json_formatter = JsonLineFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    os.makedirs(os.path.dirname(config.log_path), exist_ok=True)
    file_handler = logging.FileHandler(config.log_path)
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    return logger
