from __future__ import annotations

from marketplace import (
    AgentRepository,
    CapabilityRepository,
    DriverRepository,
    PluginRepository,
)
from marketplace.agent_repo import AgentPackage
from marketplace.capability_repo import CapabilityPackage
from marketplace.driver_repo import DriverPackage
from marketplace.plugin_repo import PluginPackage


def test_plugin_repo_publish_and_install():
    repo = PluginRepository()
    pkg = PluginPackage(name="weather", version="1.0.0", description="Weather plugin", author="x")
    pkg_id = repo.publish(pkg)
    assert isinstance(pkg_id, str)
    assert pkg_id
    installed = repo.install("weather", "1.0.0")
    assert installed.name == "weather"
    assert repo.get_versions("weather") == ["1.0.0"]


def test_plugin_repo_search():
    repo = PluginRepository()
    repo.publish(PluginPackage(name="weather", version="1.0.0", description="Weather data", author="x"))
    repo.publish(PluginPackage(name="battery", version="1.0.0", description="Battery stats", author="x"))
    results = repo.search("weather")
    assert [p.name for p in results] == ["weather"]


def test_capability_repo_register_and_discover():
    repo = CapabilityRepository()
    repo.register(
        CapabilityPackage(name="vision.detect", version="1.0.0", description="Detect objects", interface="Vision")
    )
    repo.register(
        CapabilityPackage(name="audio.transcribe", version="1.0.0", description="Transcribe audio", interface="Audio")
    )
    vision = repo.discover(prefix="vision")
    assert [c.name for c in vision] == ["vision.detect"]
    by_interface = repo.list_by_interface("Audio")
    assert [c.name for c in by_interface] == ["audio.transcribe"]


def test_driver_repo_register_and_discover():
    repo = DriverRepository()
    repo.register(DriverPackage(name="uart", version="1.0.0", transport="serial", supported_devices=["dev-a"]))
    repo.register(DriverPackage(name="spi", version="1.0.0", transport="bus", supported_devices=["dev-b"]))
    serial = repo.discover(transport="serial")
    assert [d.name for d in serial] == ["uart"]
    assert repo.get("spi").transport == "bus"


def test_agent_repo_register_and_discover():
    repo = AgentRepository()
    repo.register(AgentPackage(name="recovery", version="1.0.0", description="d", capabilities=["device.recover"]))
    repo.register(AgentPackage(name="monitor", version="1.0.0", description="d", capabilities=["device.read"]))
    recovered = repo.discover(capability="device.recover")
    assert [a.name for a in recovered] == ["recovery"]
    assert repo.get("monitor").version == "1.0.0"
