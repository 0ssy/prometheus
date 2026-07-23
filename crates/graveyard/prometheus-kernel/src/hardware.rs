use crate::event_bus::{EventBus, KernelEvent};
use crate::kernel::KernelStatus;
use hal_core::{Hal, HalRegistry, ProbeResult, Transport};

pub struct HardwareManager {
    registry: HalRegistry,
    bus: EventBus,
}

impl HardwareManager {
    pub fn new(bus: EventBus) -> Self {
        let mut registry = HalRegistry::new();
        registry.register("hal-default", Box::new(hal_core::SimulatedHal));
        Self { registry, bus }
    }

    pub fn probe(&self, transport: Transport, target: &str) -> ProbeResult {
        let result = self.registry.probe(transport, target);
        self.bus.publish(KernelEvent::hardware_probe(&result));
        result
    }

    pub fn register_driver(&mut self, target_id: impl Into<String>, driver: Box<dyn Hal>) {
        self.registry.register(target_id, driver);
    }

    pub fn status(&self) -> KernelStatus {
        KernelStatus {
            healthy: true,
            terminals: 0,
            session_db: "hardware-ok".to_string(),
        }
    }
}
