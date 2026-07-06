from __future__ import annotations

from omega.dashboard import DashboardHub
from omega.dashboard.devices import DeviceDashboard
from omega.dashboard.knowledge import KnowledgeDashboard
from omega.dashboard.logs import LogsDashboard
from omega.dashboard.metrics import MetricsDashboard
from omega.dashboard.simulation import SimulationDashboard


def test_dashboard_hub_overview():
    hub = DashboardHub()
    overview = hub.get_dashboard("overview")
    assert overview["platform"] == "Prometheus"
    assert overview["status"] == "ok"
    assert overview["devices"] == 0


def test_dashboard_hub_list_sections():
    hub = DashboardHub()
    sections = hub.list_sections()
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
    assert dash.get_graph_stats() == {"nodes": 0, "edges": 0}
    assert dash.get_recent_facts() == []
    assert dash.get_learning_history() == []


def test_simulation_dashboard():
    dash = SimulationDashboard()
    assert dash.list_simulations() == []
    results = dash.get_simulation_results("sim-1")
    assert results["simulation_id"] == "sim-1"
    assert dash.get_simulation_stats() == {"total": 0, "passed": 0, "failed": 0}


def test_metrics_dashboard():
    dash = MetricsDashboard()
    assert "metrics" in dash.get_metrics()
    assert dash.get_metric_history("cpu") == []
    assert dash.get_system_metrics() == {"cpu": 0.0, "memory": 0.0, "disk": 0.0}


def test_logs_dashboard():
    dash = LogsDashboard()
    assert dash.get_recent_logs() == []
    assert dash.get_logs_by_level("error") == []
    assert dash.search_logs("timeout") == []
