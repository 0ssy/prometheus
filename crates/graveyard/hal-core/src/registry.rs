use crate::{Hal, ProbeResult, Transport};
use std::collections::HashMap;

/// Registry mapping target identifiers to HAL drivers.
pub struct HalRegistry {
    drivers: HashMap<String, Box<dyn Hal>>,
}

impl HalRegistry {
    pub fn new() -> Self {
        Self {
            drivers: HashMap::new(),
        }
    }

    pub fn register(&mut self, target_id: impl Into<String>, driver: Box<dyn Hal>) {
        self.drivers.insert(target_id.into(), driver);
    }

    pub fn probe(&self, transport: Transport, target: &str) -> ProbeResult {
        if let Some(driver) = self.drivers.get(target) {
            driver.probe(transport, target)
        } else {
            ProbeResult {
                transport,
                target: target.to_string(),
                handshake_success: false,
                latency_ms: None,
                error: Some(format!("no driver registered for target {target}")),
            }
        }
    }

    pub fn targets(&self) -> Vec<&String> {
        self.drivers.keys().collect()
    }
}

impl Default for HalRegistry {
    fn default() -> Self {
        Self::new()
    }
}
