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
    app_name: str = "Prometheus"
    version: str = "0.5.0-gamma"

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


# Singleton — import this everywhere instead of re-instantiating
config = PrometheusConfig()
