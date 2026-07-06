"""
Prometheus Plugin SDK — Base Contract
-----------------------------------------
Every plugin is a Python class that subclasses PrometheusPlugin.
Three methods, that's the whole contract for Phase Alpha:

  - name: unique identifier
  - on_load(): called once when Prometheus starts and loads it
  - run(context): called when the plugin is invoked, gets a dict
    with access to db session + logger, returns a result dict

Keeping this contract tiny is deliberate — a wide plugin interface
is exactly how these frameworks calcify early. Grow it only when a
real plugin needs more.
"""

from abc import ABC, abstractmethod
from typing import Any


class PrometheusPlugin(ABC):
    name: str = "unnamed_plugin"
    version: str = "0.1.0"

    @abstractmethod
    def on_load(self) -> None:
        """Called once when the plugin is registered at startup."""
        ...

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Called when the plugin is invoked.
        context contains at minimum: {"db": Session, "logger": Logger}
        Must return a JSON-serializable dict.
        """
        ...
