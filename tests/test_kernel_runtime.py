from core.capabilities import CapabilityManager
from core.scheduler import TaskScheduler
from kernel.runtime import PrometheusCoreKernel


def test_kernel_runtime_health_and_permissions():
    capability_api = CapabilityManager()
    capability_api.register(
        name="device.dev-k.recover",
        target="device:dev-k",
        description="Recover",
        permissions={"device.recover"},
        executor=lambda _: {"ok": True},
    )
    scheduler = TaskScheduler()
    kernel = PrometheusCoreKernel(
        capability_api=capability_api, scheduler=scheduler, version="0.3.0"
    )
    kernel.start()
    kernel.grant_permission("system", "device.recover")

    result = kernel.execute_capability_as("system", "device.dev-k.recover", {})

    assert result == {"ok": True}
    assert kernel.health()["status"] == "ok"
    kernel.shutdown()
