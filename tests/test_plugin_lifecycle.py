"""P1 plugin lifecycle tests.

Covers the full register -> on_load -> run -> error isolation ->
unregister -> re-register cycle, contract versioning edge cases,
timeout/retry policy, a 100-cycle stress run, and the durable
``plugin_runs`` audit trail.
"""

import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from plugins.manager import PluginManager, PluginRun
from contracts.versioning import is_contract_compatible


class LifecyclePlugin:
    name = "lifecycle_plugin"
    version = "1.0.0"
    required_contract_version = "1.0.0"
    on_load_calls = 0
    runs = 0

    def on_load(self) -> None:
        LifecyclePlugin.on_load_calls += 1

    def run(self, context: dict) -> dict:
        LifecyclePlugin.runs += 1
        return {"ok": True, "echo": context.get("value")}


class CrashPlugin(LifecyclePlugin):
    name = "crash_plugin"

    def run(self, context: dict) -> dict:
        raise RuntimeError("boom")


class SlowPlugin(LifecyclePlugin):
    name = "slow_plugin"

    def run(self, context: dict) -> dict:
        time.sleep(10)
        return {"ok": True}


@pytest.fixture(autouse=True)
def _reset_counters():
    LifecyclePlugin.on_load_calls = 0
    LifecyclePlugin.runs = 0
    yield


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Isolated SQLite engine/session so plugin_runs persistence is real."""
    db_path = tmp_path / "prometheus.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    session_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    monkeypatch.setattr(cd, "engine", engine)
    monkeypatch.setattr(cd, "SessionLocal", session_factory)
    cd.init_db()
    yield session_factory
    engine.dispose()


class TestPluginLifecycle:
    def test_register_on_load_run_cycle(self):
        manager = PluginManager()
        plugin = LifecyclePlugin()
        manager.register(plugin)
        assert manager.get("lifecycle_plugin") is plugin
        result = manager.run("lifecycle_plugin", {"value": 42})
        assert result == {"ok": True, "echo": 42}
        assert LifecyclePlugin.on_load_calls == 1
        assert LifecyclePlugin.runs == 1

    def test_run_isolates_plugin_exception(self):
        manager = PluginManager()
        manager.register(CrashPlugin())
        result = manager.run("crash_plugin", {})
        assert "error" in result
        assert "boom" in result["error"]
        # Kernel stays healthy: a subsequent valid run succeeds.
        manager.register(LifecyclePlugin())
        ok = manager.run("lifecycle_plugin", {"value": 1})
        assert ok.get("ok") is True
        assert "error" not in ok

    def test_run_timeout_aborts_hung_plugin(self):
        manager = PluginManager()
        manager.register(SlowPlugin())
        start = time.monotonic()
        result = manager.run("slow_plugin", {}, timeout=0.5)
        elapsed = time.monotonic() - start
        assert "error" in result
        assert result["error"] == "timeout"
        assert elapsed < 5

    def test_unregister_then_reregister(self):
        manager = PluginManager()
        manager.register(LifecyclePlugin())
        assert manager.get("lifecycle_plugin") is not None
        manager.unregister("lifecycle_plugin")
        assert manager.get("lifecycle_plugin") is None
        # Re-register must re-run on_load and run again.
        manager.register(LifecyclePlugin())
        ok = manager.run("lifecycle_plugin", {"value": 1})
        assert ok.get("ok") is True
        assert "error" not in ok
        assert LifecyclePlugin.on_load_calls == 2

    def test_contract_major_mismatch_rejects(self):
        class FuturePlugin(LifecyclePlugin):
            name = "future_plugin"
            required_contract_version = "2.0.0"

        manager = PluginManager()
        with pytest.raises(RuntimeError, match="Incompatible contract version"):
            manager.register(FuturePlugin())

    def test_contract_minor_forward_compat_passes(self):
        # Runtime 1.1.0 satisfies a plugin that only needs 1.0.0.
        assert is_contract_compatible("1.0.0", "1.1.0") is True
        # Runtime 1.0.0 cannot satisfy a plugin needing 1.1.0.
        assert is_contract_compatible("1.1.0", "1.0.0") is False

    def test_stress_100_cycles_high_success(self):
        manager = PluginManager()
        manager.register(LifecyclePlugin())
        success = 0
        for _ in range(100):
            result = manager.run("lifecycle_plugin", {"value": 1})
            if "error" not in result:
                success += 1
        assert success >= 99  # >= 99% plugin load/run success (P1 KPI)

    def test_plugin_runs_audit_trail_persisted(self, temp_db):
        manager = PluginManager()
        manager.register(LifecyclePlugin())
        manager.run("lifecycle_plugin", {"value": 7})
        manager.register(CrashPlugin())
        manager.run("crash_plugin", {})

        with temp_db() as session:
            runs = session.query(PluginRun).all()
        names = sorted(r.plugin_name for r in runs)
        assert names == ["crash_plugin", "lifecycle_plugin"]
        by_name = {r.plugin_name: r for r in runs}
        assert by_name["lifecycle_plugin"].status == "success"
        assert by_name["crash_plugin"].status == "error"
        assert by_name["crash_plugin"].error == "boom"
        assert by_name["lifecycle_plugin"].duration_ms is not None
        assert by_name["lifecycle_plugin"].duration_ms >= 0
