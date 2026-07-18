from __future__ import annotations

from dashboard import DashboardHub
from dashboard.devices import DeviceDashboard
from dashboard.knowledge import KnowledgeDashboard
from dashboard.logs import LogsDashboard
from dashboard.metrics import MetricsDashboard
from dashboard.simulation import SimulationDashboard


def test_dashboard_hub_overview():
    hub = DashboardHub()
    overview = hub.get_dashboard("overview")
    assert overview.platform_name == "Prometheus"
    assert overview.status == "operational"
    assert overview.total_devices == 0


def test_dashboard_hub_list_sections():
    hub = DashboardHub()
    sections = hub.get_dashboard("all")["sections"]
    assert "overview" in sections


def test_device_dashboard():
    dash = DeviceDashboard()
    assert dash.list_devices() == []
    details = dash.get_device_details("dev-1")
    assert details["device_id"] == "dev-1"
    health = dash.get_device_health("dev-1")
    assert health["device_id"] == "dev-1"


def test_knowledge_dashboard():
    dash = KnowledgeDashboard()
    assert dash.get_graph_stats() == {"nodes": 0, "edges": 0, "facts": 0}
    assert dash.get_recent_facts() == []
    assert dash.get_learning_history() == []


def test_simulation_dashboard():
    dash = SimulationDashboard()
    assert dash.list_simulations() == []
    results = dash.get_simulation_results("sim-1")
    assert results["simulation_id"] == "sim-1"
    assert dash.get_simulation_stats() == {
        "total_simulations": 0,
        "completed": 0,
        "running": 0,
        "failed": 0,
    }


def test_metrics_dashboard():
    dash = MetricsDashboard()
    assert dash.get_metrics() == {}
    assert dash.get_metric_history("cpu") == []
    assert dash.get_system_metrics() == {"cpu_percent": 0.0, "memory_percent": 0.0, "disk_percent": 0.0}


def test_logs_dashboard():
    dash = LogsDashboard()
    assert dash.get_recent_logs() == []
    assert dash.get_logs_by_level("error") == []
    assert dash.search_logs("timeout") == []
