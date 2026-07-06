"""
Echo Plugin — Reference Implementation
-----------------------------------------
This exists purely to prove the plugin contract works: load it,
run it, get a result. When you write your first real plugin, copy
this file's shape, not its logic.
"""

from plugins.base import PrometheusPlugin
from memory.store import remember


class EchoPlugin(PrometheusPlugin):
    name = "echo"
    version = "0.1.0"

    def on_load(self) -> None:
        # Real plugins might load models, open connections, etc.
        pass

    def run(self, context: dict) -> dict:
        message = context.get("message", "")
        db = context["db"]
        remember(
            db,
            content=f"Echo plugin ran with: {message}",
            tag="plugin_run",
            source="echo",
        )
        return {"echoed": message, "plugin": self.name}
