from core.observability import ObservabilityStore


def test_events_per_sec_computed():
    store = ObservabilityStore()
    store.record_event("device.connected", {"device_id": "d1"})
    store.record_event("device.connected", {"device_id": "d2"})
    snap = store.snapshot()
    assert snap["events_per_sec"] >= 0


def test_commands_per_sec_computed():
    store = ObservabilityStore()
    store.record_command("device.status")
    store.record_command("device.diagnose")
    snap = store.snapshot()
    assert snap["commands_per_sec"] >= 0


def test_record_command_increments_metric():
    store = ObservabilityStore()
    store.record_command("device.status")
    snap = store.snapshot()
    assert snap["metrics"]["commands.device.status"] == 1


def test_snapshot_includes_subsystems_when_status_provided():
    store = ObservabilityStore()
    status = {
        "kernel": "Running",
        "knowledge": "Healthy",
        "simulation": "Idle",
        "reasoning": "Ready",
        "hardware": "Active",
        "agents": 2,
        "plugins": 3,
        "devices": 1,
        "workflows": "Idle",
        "background_tasks": "Idle",
        "storage": "Idle",
    }
    snap = store.snapshot(status=status)
    assert snap["subsystems"]["kernel"] == "Running"
    assert snap["subsystems"]["agents"] == 2
