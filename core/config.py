"""
Prometheus Config Manager
-------------------------
Single source of truth for settings. Everything else in the system
reads config from here — nothing should read os.environ directly
outside this file. That's the rule that keeps config sane as this grows.
"""

import os
from dataclasses import dataclass, field


@dataclass
class PrometheusConfig:
    app_name: str = "Prometheus Engineering Intelligence Platform"
    version: str = "1.0.0-rc1"

    # Storage
    db_path: str = field(
        default_factory=lambda: os.environ.get(
            "PROMETHEUS_DB_PATH", "./data/prometheus.db"
        )
    )

    # API
    api_host: str = field(
        default_factory=lambda: os.environ.get("PROMETHEUS_API_HOST", "127.0.0.1")
    )
    api_port: int = field(
        default_factory=lambda: int(os.environ.get("PROMETHEUS_API_PORT", "8000"))
    )

    # Logging
    log_level: str = field(
        default_factory=lambda: os.environ.get("PROMETHEUS_LOG_LEVEL", "INFO")
    )
    log_path: str = field(
        default_factory=lambda: os.environ.get(
            "PROMETHEUS_LOG_PATH", "./data/prometheus.log"
        )
    )

    # Plugins
    plugins_dir: str = field(
        default_factory=lambda: os.environ.get(
            "PROMETHEUS_PLUGINS_DIR", "./plugins/installed"
        )
    )

    # LLM / Assistant
    llm_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "PROMETHEUS_LLM_BASE_URL", "http://localhost:1234/v1"
        )
    )
    llm_model: str = field(
        default_factory=lambda: os.environ.get("PROMETHEUS_LLM_MODEL", "local-model")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.environ.get("PROMETHEUS_LLM_API_KEY", "")
    )

    # Native multi-language runtime orchestration (P2+)
    native_runtime_mode: str = field(
        default_factory=lambda: os.environ.get("PROMETHEUS_NATIVE_RUNTIME", "auto")
    )  # off|auto|on
    go_controlplane_url: str = field(
        default_factory=lambda: os.environ.get(
            "PROMETHEUS_GO_CONTROLPLANE_URL", "http://127.0.0.1:8080"
        )
    )
    go_billing_url: str = field(
        default_factory=lambda: os.environ.get(
            "PROMETHEUS_GO_BILLING_URL", "http://127.0.0.1:8081"
        )
    )
    native_runtime_health_timeout_seconds: float = field(
        default_factory=lambda: float(
            os.environ.get("PROMETHEUS_NATIVE_RUNTIME_HEALTH_TIMEOUT", "8")
        )
    )


# Singleton — import this everywhere instead of re-instantiating
config = PrometheusConfig()
