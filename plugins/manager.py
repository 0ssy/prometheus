"""
Prometheus Plugin Manager
-----------------------------------------
Discovers plugin classes and keeps a registry. Phase Alpha loads
plugins that are Python classes registered directly (see
plugins/installed/echo_plugin.py for the reference example) —
dynamic filesystem discovery of arbitrary third-party plugins is a
Phase Beta/Gamma concern once there's a security model for it.
"""

from .base import PrometheusPlugin
from contracts.plugin import PluginApi
from contracts.event_bus import EventBus
from contracts.versioning import CONTRACT_VERSION, validate_contract_compatibility
from api.events import PluginRanEvent, PluginErrorEvent
import uuid
from core.logger import get_logger
from core.event_bus import event_bus as default_event_bus
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Text

from core.database import Base

import concurrent.futures

logger = get_logger(__name__)


class PluginRun(Base):
    """Durable audit trail of every plugin execution (P1 lifecycle)."""

    __tablename__ = "plugin_runs"

    run_id = Column(String, primary_key=True)
    plugin_name = Column(String, index=True, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="running", nullable=False)
    error = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)


class PluginManager(PluginApi):
    def __init__(self, event_bus: EventBus | None = None):
        self._plugins: dict[str, PrometheusPlugin] = {}
        self._event_bus = event_bus or default_event_bus

    def register(self, plugin: PrometheusPlugin) -> None:
        if plugin.name in self._plugins:
            logger.warning(f"Plugin '{plugin.name}' already registered — overwriting")
        validate_contract_compatibility(plugin.required_contract_version, CONTRACT_VERSION)
        plugin.on_load()
        self._plugins[plugin.name] = plugin
        logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")

    def get(self, name: str) -> PrometheusPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [{"name": p.name, "version": p.version} for p in self._plugins.values()]

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)
        logger.info("Unloaded plugin: %s", name)

    def run(self, name: str, context: dict, timeout: float | None = None) -> dict:
        plugin = self.get(name)
        if plugin is None:
            raise ValueError(f"No such plugin: {name}")

        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        self._persist_run(run_id, name, started_at, status="running")

        try:
            if timeout is not None and timeout > 0:
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    future = executor.submit(plugin.run, context)
                    try:
                        result = future.result(timeout=timeout)
                    except concurrent.futures.TimeoutError:
                        logger.warning("Plugin '%s' timed out after %.2fs; aborting", name, timeout)
                        self._event_bus.publish(
                            PluginErrorEvent(plugin_name=name, error="timeout")
                        )
                        self._persist_run(run_id, name, started_at, status="timeout", error="timeout")
                        return {"error": "timeout"}
                finally:
                    executor.shutdown(wait=False)
            else:
                result = plugin.run(context)
        except Exception as exc:
            logger.exception("Plugin '%s' raised an error", name)
            self._event_bus.publish(
                PluginErrorEvent(plugin_name=name, error=str(exc))
            )
            self._persist_run(run_id, name, started_at, status="error", error=str(exc))
            return {"error": str(exc)}
        self._persist_run(run_id, name, started_at, status="success")
        self._event_bus.publish(PluginRanEvent(plugin_name=name, result=result))
        return result

    def _persist_run(
        self,
        run_id: str,
        name: str,
        started_at: datetime,
        status: str,
        error: str | None = None,
    ) -> None:
        """Best-effort write to the ``plugin_runs`` table. Degrades
        silently when the database is unavailable (e.g. unit tests)."""
        try:
            from core.database import SessionLocal

            finished_at = datetime.now(timezone.utc)
            duration_ms = (finished_at - started_at).total_seconds() * 1000.0
            with SessionLocal() as session:
                existing = session.get(PluginRun, run_id)
                if existing is None:
                    session.add(
                        PluginRun(
                            run_id=run_id,
                            plugin_name=name,
                            started_at=started_at,
                            finished_at=finished_at,
                            status=status,
                            error=error,
                            duration_ms=duration_ms,
                        )
                    )
                else:
                    existing.finished_at = finished_at
                    existing.status = status
                    existing.error = error
                    existing.duration_ms = duration_ms
                session.commit()
        except Exception:
            logger.debug("Plugin run not persisted (DB unavailable)")


plugin_manager = PluginManager()
