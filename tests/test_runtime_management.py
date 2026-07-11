from __future__ import annotations

from omega.runtime_management import LifecycleManager, MemoryManager, ResourceManager
from omega.runtime_management.lifecycle_manager import LifecycleState
from omega.runtime_management.resource_manager import ResourceLimits


def test_resource_manager_get_usage():
    manager = ResourceManager()
    usage = manager.get_usage()
    assert usage.cpu_percent >= 0.0
    assert usage.memory_mb >= 0.0
    assert usage.active_connections >= 0


def test_resource_manager_check_limits():
    manager = ResourceManager()
    limits = ResourceLimits(max_cpu_percent=100000.0, max_memory_mb=100000.0, max_connections=100000)
    result = manager.check_limits(limits)
    assert result["within_limits"] is True
    assert result["violations"] == []


def test_resource_manager_to_dict_no_attribute_error():
    manager = ResourceManager()
    data = manager.to_dict()
    assert data["throttled"] is False
    assert data["throttle_reason"] is None


def test_memory_manager_get_stats():
    manager = MemoryManager()
    stats = manager.get_stats()
    assert stats.total_mb >= 0.0
    assert stats.available_mb >= 0.0


def test_memory_manager_collect():
    manager = MemoryManager()
    collected = manager.collect()
    assert isinstance(collected, int)


def test_lifecycle_manager_transition():
    manager = LifecycleManager()
    assert manager.get_state() == LifecycleState.INITIALIZING
    manager.transition(LifecycleState.RUNNING)
    assert manager.get_state() == LifecycleState.RUNNING
    history = manager.get_history()
    assert len(history) == 1
    assert history[0].state == LifecycleState.RUNNING


def test_lifecycle_manager_hooks():
    manager = LifecycleManager()
    calls = []
    manager.register_hook("on_transition", lambda: calls.append("fired"))
    manager.transition(LifecycleState.RUNNING)
    assert len(calls) == 1
    manager.execute_hooks("on_shutdown")
