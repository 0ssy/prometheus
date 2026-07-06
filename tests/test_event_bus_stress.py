from api.events import PluginRanEvent
from core.event_bus import InMemoryEventBus


def test_event_bus_high_volume_delivery():
    bus = InMemoryEventBus()
    count_a = 0
    count_b = 0
    total_events = 50000

    def handler_a(event):
        nonlocal count_a
        if event.plugin_name.startswith("p"):
            count_a += 1

    def handler_b(event):
        nonlocal count_b
        if event.result.get("ok") is True:
            count_b += 1

    bus.subscribe("plugin.ran", handler_a)
    bus.subscribe("plugin.ran", handler_b)

    for i in range(total_events):
        bus.publish(PluginRanEvent(plugin_name=f"p{i}", result={"ok": True}))

    assert count_a == total_events
    assert count_b == total_events
