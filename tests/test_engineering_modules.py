"""
Phase 4 — Engineering Intelligence integration tests.
Validates all 10 discipline modules and EngineeringService registration.
"""

import os
import tempfile

import pytest

from services.engineering_service import EngineeringService


@pytest.fixture
def service():
    return EngineeringService()


class TestEngineeringServiceRegistration:
    def test_lists_all_modules(self, service):
        modules = service.list_modules()
        expected = [
            "firmware",
            "boot_chain",
            "partition",
            "recovery",
            "crypto",
            "embedded",
            "robotics",
            "mechanical",
            "electrical",
            "networking",
            "cybersecurity",
            "ai",
            "data",
            "cloud",
        ]
        for mod in expected:
            assert mod in modules

    def test_unknown_module_raises(self, service):
        with pytest.raises(ValueError, match="Unknown engineering module"):
            service.execute_workflow("nonexistent", "do_thing", {})


class TestFirmwareModule:
    def test_inspect_firmware(self, service):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\x00" * 64)
            path = f.name
        try:
            result = service.execute_workflow("firmware", "inspect", {"path": path, "ownership_declared": True})
            assert result["format"] in ("esp32_image", "unknown_format")
            assert "sha256" in result
            assert result["size_bytes"] >= 0
        finally:
            os.unlink(path)


class TestBootChainModule:
    def test_analyze_valid(self, service):
        result = service.execute_workflow(
            "boot_chain",
            "analyze",
            {"firmware_bytes": b"abc", "signature": b"sig", "public_key_bytes": b"key" * 8},
        )
        assert result["status"] in ("valid", "invalid", "unknown")
        assert "firmware_hash" in result


class TestPartitionModule:
    def test_read_table_requires_ownership(self, service):
        with pytest.raises(PermissionError):
            service.execute_workflow("partition", "read_table", {"disk_path": "/dev/null", "ownership_declared": False})


class TestRecoveryModule:
    def test_plan_recovery(self, service):
        result = service.execute_workflow(
            "recovery", "plan", {"device_id": "dev1", "boot_chain_status": "valid", "partition_scheme": "gpt"}
        )
        assert result["device_id"] == "dev1"
        assert "steps" in result


class TestCryptoModule:
    def test_sha256(self, service):
        result = service.execute_workflow("crypto", "sha256", {"data": b"hello"})
        assert "hash" in result
        assert len(result["hash"]) == 64

    def test_verify(self, service):
        result = service.execute_workflow(
            "crypto", "verify", {"public_key_bytes": b"\x00" * 32, "signature": b"\x00" * 64, "data": b"hello"}
        )
        assert "valid" in result


class TestEmbeddedModule:
    def test_flash_firmware(self, service):
        result = service.execute_workflow(
            "embedded", "flash_firmware", {"device_id": "esp32_01", "firmware_path": "/tmp/fw.bin"}
        )
        assert result["status"] == "success"
        assert result["device_id"] == "esp32_01"

    def test_read_sensor(self, service):
        result = service.execute_workflow("embedded", "read_sensor", {"sensor_id": "temp_1", "sensor_type": "temperature", "value": 24.5, "unit": "C"})
        assert result["sensor_type"] == "temperature"
        assert result["value"] == 24.5

    def test_configure_rtos(self, service):
        result = service.execute_workflow("embedded", "configure_rtos", {"device_id": "stm32_01", "rtos": "FreeRTOS", "scheduler": "preemptive", "tick_rate_hz": 1000})
        assert result["rtos"] == "FreeRTOS"
        assert result["tick_rate_hz"] == 1000

    def test_debug_jtag(self, service):
        result = service.execute_workflow("embedded", "debug_jtag", {"device_id": "stm32_01"})
        assert "registers" in result
        assert result["halted"] is False

    def test_build_firmware(self, service):
        result = service.execute_workflow("embedded", "build_firmware", {"device_id": "esp32_01", "toolchain": "gcc-arm-none-eabi", "target": "cortex-m4"})
        assert result["status"] == "success"
        assert result["size_bytes"] > 0


class TestRoboticsModule:
    def test_run_slam(self, service):
        result = service.execute_workflow("robotics", "run_slam", {"robot_id": "robot_01"})
        assert result["map_size_m2"] > 0
        assert result["landmarks"] > 0

    def test_plan_path(self, service):
        result = service.execute_workflow("robotics", "plan_path", {"robot_id": "robot_01", "start": [0, 0], "goal": [10, 10]})
        assert len(result["waypoints"]) >= 2
        assert result["estimated_time_s"] > 0

    def test_control_motor(self, service):
        result = service.execute_workflow("robotics", "control_motor", {"robot_id": "robot_01", "joint": "shoulder", "velocity": 1.5, "torque": 12.0})
        assert result["status"] == "executed"

    def test_capture_vision(self, service):
        result = service.execute_workflow("robotics", "capture_vision", {"robot_id": "robot_01", "camera": "front_rgb"})
        assert result["resolution"] == "640x480"
        assert result["frame_count"] == 1

    def test_simulate_physics(self, service):
        result = service.execute_workflow("robotics", "simulate_physics", {"robot_id": "robot_01", "duration_s": 10.0})
        assert result["collisions"] >= 0
        assert 0.0 <= result["stability_score"] <= 1.0


class TestMechanicalModule:
    def test_analyze_stress(self, service):
        result = service.execute_workflow("mechanical", "analyze_stress", {"part_id": "gear_01", "max_stress_mpa": 100.0, "yield_mpa": 250.0})
        assert "safety_factor" in result
        assert result["safety_factor"] >= 1.5

    def test_run_motion_simulation(self, service):
        result = service.execute_workflow("mechanical", "run_motion_simulation", {"assembly_id": "arm_01", "joints": 6})
        assert result["joints"] == 6
        assert result["interference_detected"] is False

    def test_generate_cam_toolpath(self, service):
        result = service.execute_workflow("mechanical", "generate_cam_toolpath", {"part_id": "bracket_01", "tool": "endmill_6mm", "passes": 3})
        assert result["passes"] == 3
        assert result["total_length_m"] > 0

    def test_check_materials(self, service):
        result = service.execute_workflow("mechanical", "check_materials", {"part_id": "bracket_01", "material": "aluminum_6061"})
        assert result["material"] == "aluminum_6061"
        assert result["density_kg_m3"] > 0


class TestElectricalModule:
    def test_simulate_circuit(self, service):
        result = service.execute_workflow("electrical", "simulate_circuit", {"circuit_id": "pwr_01"})
        assert result["converged"] is True
        assert result["max_voltage_v"] > 0

    def test_analyze_power(self, service):
        result = service.execute_workflow("electrical", "analyze_power", {"circuit_id": "pwr_01"})
        assert result["total_power_w"] > 0
        assert result["efficiency_pct"] > 0

    def test_capture_oscilloscope(self, service):
        result = service.execute_workflow("electrical", "capture_oscilloscope", {"channel": "CH1"})
        assert result["sample_rate_hz"] > 0
        assert result["samples"] > 0

    def test_route_pcb(self, service):
        result = service.execute_workflow("electrical", "route_pcb", {"board_id": "brd_01"})
        assert result["traces"] > 0
        assert result["drc_passed"] is True

    def test_check_signal_integrity(self, service):
        result = service.execute_workflow("electrical", "check_signal_integrity", {"trace_id": "trace_01"})
        assert result["impedance_ohm"] > 0
        assert result["passed"] is True


class TestNetworkingModule:
    def test_capture_packets(self, service):
        result = service.execute_workflow("networking", "capture_packets", {"interface": "eth0", "duration_s": 10.0})
        assert result["packets"] > 0
        assert "TCP" in result["protocols"]

    def test_analyze_topology(self, service):
        result = service.execute_workflow("networking", "analyze_topology", {"network_id": "lan_01"})
        assert len(result["nodes"]) > 0
        assert result["edges"] > 0

    def test_diagnose_connectivity(self, service):
        result = service.execute_workflow("networking", "diagnose_connectivity", {"source": "192.168.1.100", "destination": "192.168.1.1"})
        assert result["latency_ms"] >= 0
        assert result["packet_loss_pct"] >= 0

    def test_scan_ports(self, service):
        result = service.execute_workflow("networking", "scan_ports", {"target": "192.168.1.1"})
        assert len(result["ports_open"]) > 0
        assert result["scan_time_ms"] > 0

    def test_monitor_bandwidth(self, service):
        result = service.execute_workflow("networking", "monitor_bandwidth", {"interface": "eth0"})
        assert result["throughput_mbps"] > 0
        assert 0 <= result["utilization_pct"] <= 100


class TestCybersecurityModule:
    def test_scan_vulnerabilities(self, service):
        result = service.execute_workflow("cybersecurity", "scan_vulnerabilities", {"target": "srv_01"})
        assert len(result["cves"]) > 0
        assert result["risk_score"] > 0

    def test_audit_configuration(self, service):
        result = service.execute_workflow("cybersecurity", "audit_configuration", {"target": "srv_01"})
        assert result["checks_run"] > 0
        assert result["passed"] + result["failed"] == result["checks_run"]

    def test_analyze_logs(self, service):
        result = service.execute_workflow("cybersecurity", "analyze_logs", {"target": "srv_01", "log_source": "syslog"})
        assert result["events_analyzed"] > 0
        assert result["severity"] in ("low", "medium", "high", "critical")

    def test_verify_compliance(self, service):
        result = service.execute_workflow("cybersecurity", "verify_compliance", {"target": "srv_01", "framework": "SOC2"})
        assert result["controls_assessed"] > 0
        assert result["controls_passed"] <= result["controls_assessed"]

    def test_check_patch_status(self, service):
        result = service.execute_workflow("cybersecurity", "check_patch_status", {"target": "srv_01", "os": "linux"})
        assert result["pending_updates"] >= 0
        assert result["critical_pending"] <= result["pending_updates"]


class TestAIModule:
    def test_manage_model(self, service):
        result = service.execute_workflow("ai", "manage_model", {"model_id": "model_01", "action": "load"})
        assert result["status"] == "success"
        assert result["provider"] == "aether"

    def test_run_prompt(self, service):
        result = service.execute_workflow("ai", "run_prompt", {"model_id": "model_01", "prompt": "Hello"})
        assert len(result["response"]) > 0
        assert result["tokens_used"] > 0

    def test_evaluate_model(self, service):
        result = service.execute_workflow("ai", "evaluate_model", {"model_id": "model_01", "benchmark": "mmlu", "score": 0.85})
        assert result["score"] == 0.85
        assert result["passed"] is True

    def test_fine_tune(self, service):
        result = service.execute_workflow("ai", "fine_tune", {"model_id": "model_01", "dataset": "custom", "epochs": 3})
        assert result["epochs"] == 3
        assert result["status"] == "completed"

    def test_run_inference(self, service):
        result = service.execute_workflow("ai", "run_inference", {"model_id": "model_01", "input_tokens": 128})
        assert result["input_tokens"] == 128
        assert result["throughput_tps"] > 0

    def test_build_rag_index(self, service):
        result = service.execute_workflow("ai", "build_rag_index", {"index_id": "idx_01", "documents": 100})
        assert result["documents_indexed"] == 100
        assert result["index_type"] == "hnsw"


class TestDataModule:
    def test_query_database(self, service):
        result = service.execute_workflow("data", "query_database", {"database": "prometheus", "query": "SELECT 1"})
        assert result["database"] == "prometheus"
        assert result["execution_time_ms"] > 0

    def test_run_etl(self, service):
        result = service.execute_workflow("data", "run_etl", {"pipeline_id": "etl_01", "source": "csv", "destination": "sqlite"})
        assert result["records_processed"] > 0
        assert result["errors"] == 0

    def test_build_knowledge_graph(self, service):
        result = service.execute_workflow("data", "build_knowledge_graph", {"graph_id": "kg_01"})
        assert result["nodes"] > 0
        assert result["edges"] > 0

    def test_analyze_vector_store(self, service):
        result = service.execute_workflow("data", "analyze_vector_store", {"store_id": "vec_01"})
        assert result["vectors"] > 0
        assert result["dimension"] > 0

    def test_export_dataset(self, service):
        result = service.execute_workflow("data", "export_dataset", {"dataset_id": "ds_01", "format": "jsonl", "records": 1000})
        assert result["records"] == 1000
        assert result["format"] == "jsonl"


class TestCloudModule:
    def test_deploy_container(self, service):
        result = service.execute_workflow("cloud", "deploy_container", {"service": "api", "region": "eastus"})
        assert result["status"] == "running"
        assert "prometheus.cloud" in result["endpoint"]

    def test_scale_service(self, service):
        result = service.execute_workflow("cloud", "scale_service", {"service": "api", "replicas": 3})
        assert result["replicas"] == 3
        assert result["cpu_cores"] > 0

    def test_check_health(self, service):
        result = service.execute_workflow("cloud", "check_health", {"service": "api"})
        assert result["healthy"] is True
        assert result["uptime_s"] > 0

    def test_pull_logs(self, service):
        result = service.execute_workflow("cloud", "pull_logs", {"service": "api", "since": "1h"})
        assert result["lines"] > 0
        assert "info" in result["level_counts"]

    def test_manage_secrets(self, service):
        result = service.execute_workflow("cloud", "manage_secrets", {"secret_id": "db_pw", "action": "rotate"})
        assert result["action"] == "rotate"
        assert result["status"] == "success"


class TestEngineeringAPI:
    def test_list_modules_endpoint(self):
        from fastapi.testclient import TestClient
        import backend.main as main_module

        with TestClient(main_module.app) as client:
            response = client.get("/engineering/modules")
            assert response.status_code == 200
            data = response.json()
            assert "modules" in data
            assert "embedded" in data["modules"]
            assert "robotics" in data["modules"]
            assert "cloud" in data["modules"]

    def test_execute_workflow_endpoint(self):
        from fastapi.testclient import TestClient
        import backend.main as main_module

        with TestClient(main_module.app) as client:
            response = client.post(
                "/engineering/execute",
                json={"module_name": "networking", "workflow": "capture_packets", "payload": {"interface": "eth0", "duration_s": 5.0}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "data" in data
            assert data["data"]["interface"] == "eth0"
            assert data["data"]["packets"] > 0
